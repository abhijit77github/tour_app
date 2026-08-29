import unittest
from copy import deepcopy
from contextlib import contextmanager
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import access_control as access_control_router_module
from backend.routers.access_control import router as access_control_router
from backend.utils.authorization import ensure_operator_access_context


class FakeCursor:
    def __init__(self, docs):
        self.docs = [deepcopy(doc) for doc in docs]

    def sort(self, field, direction):
        reverse = direction == -1
        self.docs.sort(key=lambda doc: doc.get(field), reverse=reverse)
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.docs):
            raise StopAsyncIteration
        value = deepcopy(self.docs[self._index])
        self._index += 1
        return value


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, modified_count=0):
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in (docs or [])]

    def _matches(self, doc, query):
        for key, value in query.items():
            if doc.get(key) != value:
                return False
        return True

    def find(self, query):
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query):
        for doc in self.docs:
          if self._matches(doc, query):
              return deepcopy(doc)
        return None

    async def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault('_id', ObjectId())
        self.docs.append(stored)
        return FakeInsertResult(stored['_id'])

    async def update_one(self, query, update, upsert=False):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query):
                updated = deepcopy(doc)
                for key, value in deepcopy(update.get('$set', {})).items():
                    updated[key] = value
                for key, value in deepcopy(update.get('$setOnInsert', {})).items():
                    updated.setdefault(key, value)
                self.docs[index] = updated
                return FakeUpdateResult(modified_count=1)
        if upsert:
            new_doc = deepcopy(query)
            for key, value in deepcopy(update.get('$setOnInsert', {})).items():
                new_doc[key] = value
            for key, value in deepcopy(update.get('$set', {})).items():
                new_doc[key] = value
            await self.insert_one(new_doc)
            return FakeUpdateResult(modified_count=1)
        return FakeUpdateResult(modified_count=0)


class FakeDB:
    def __init__(
        self,
        *,
        users=None,
        admins=None,
        operator_profiles=None,
        organizations=None,
        organization_memberships=None,
        access_roles=None,
    ):
        self.users = FakeCollection(users)
        self.admins = FakeCollection(admins)
        self.operator_profiles = FakeCollection(operator_profiles)
        self.organizations = FakeCollection(organizations)
        self.organization_memberships = FakeCollection(organization_memberships)
        self.access_roles = FakeCollection(access_roles)


def build_test_client(*, db, operator_context=None, admin_context=None, current_admin=None):
    app = FastAPI()
    app.include_router(access_control_router)

    async def override_operator_context():
        return operator_context

    async def override_admin_context():
        return admin_context

    async def override_current_admin():
        return current_admin or {"_id": "admin-1", "email": "owner@tourapp.local", "role": "super_admin", "full_name": "Owner Admin"}

    app.dependency_overrides[access_control_router_module.get_current_operator_access_context] = override_operator_context
    app.dependency_overrides[access_control_router_module.get_current_admin_access_context] = override_admin_context
    app.dependency_overrides[access_control_router_module.get_current_admin] = override_current_admin
    return TestClient(app)


@contextmanager
def patched_database(db):
    async def override_db():
        return db

    with patch.object(access_control_router_module, 'get_database', override_db):
        yield


class AccessControlApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_operator_access_context_provisions_org_and_owner_membership(self):
        profile_id = ObjectId()
        fake_db = FakeDB(
            operator_profiles=[
                {
                    '_id': profile_id,
                    'user_id': 'user-1',
                    'business_name': 'Sky Trails',
                    'contact_number': '+910000000000',
                    'serving_areas': [],
                }
            ]
        )

        context = await ensure_operator_access_context(
            fake_db,
            user={'_id': 'user-1', 'email': 'owner@skytrails.local', 'full_name': 'Sky Owner', 'user_type': 'operator'},
        )

        self.assertEqual(context['organization']['name'], 'Sky Trails')
        self.assertEqual(context['membership']['role_keys'], ['operator_owner'])
        self.assertIn('operator.team.manage', context['permissions'])
        self.assertEqual(context['operator_profile']['serving_areas'], [])
        self.assertEqual(len(fake_db.organizations.docs), 1)
        self.assertEqual(len(fake_db.organization_memberships.docs), 1)
        self.assertEqual(fake_db.operator_profiles.docs[0]['organization_id'], context['organization']['_id'])

    async def test_ensure_operator_access_context_includes_serving_areas_for_downstream_validators(self):
        profile_id = ObjectId()
        serving_areas = [
            {
                'area_name': 'Mysore',
                'state': 'Karnataka',
                'country': 'India',
            }
        ]
        fake_db = FakeDB(
            operator_profiles=[
                {
                    '_id': profile_id,
                    'user_id': 'user-2',
                    'business_name': 'Heritage Routes',
                    'contact_number': '+910000000001',
                    'serving_areas': serving_areas,
                }
            ]
        )

        context = await ensure_operator_access_context(
            fake_db,
            user={'_id': 'user-2', 'email': 'owner@heritage.local', 'full_name': 'Heritage Owner', 'user_type': 'operator'},
        )

        self.assertEqual(context['operator_profile']['serving_areas'], serving_areas)


class AccessControlRouterTests(unittest.TestCase):
    def test_operator_team_member_can_be_created_and_updated(self):
        organization_id = str(ObjectId())
        fake_db = FakeDB()
        operator_context = {
            'principal': {'_id': 'owner-1', 'email': 'owner@op.local', 'full_name': 'Owner'},
            'organization': {'_id': organization_id, 'name': 'Op Org', 'slug': 'op-org', 'organization_type': 'operator', 'status': 'active'},
            'permissions': ['operator.team.manage'],
            'role_templates': [],
        }
        client = build_test_client(db=fake_db, operator_context=operator_context)

        with patched_database(fake_db):
            create_response = client.post(
                '/operators/team',
                json={
                    'full_name': 'Sales Rep',
                    'email': 'sales@op.local',
                    'phone': '+911111111111',
                    'password': 'Temporary123!',
                    'role_keys': ['operator_sales'],
                    'permission_overrides': {'allow': [], 'deny': []},
                    'scope_constraints': {},
                },
            )

            self.assertEqual(create_response.status_code, 201)
            created = create_response.json()['member']
            self.assertTrue(create_response.json()['created_account'])
            self.assertEqual(created['role_keys'], ['operator_sales'])
            self.assertIn('operator.quotes.respond', created['permissions'])

            update_response = client.patch(
                f"/operators/team/{created['_id']}",
                json={'role_keys': ['operator_finance'], 'membership_status': 'suspended'},
            )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()['member']
        self.assertEqual(updated['role_keys'], ['operator_finance'])
        self.assertEqual(updated['membership_status'], 'suspended')
        self.assertIn('operator.billing.read', updated['permissions'])

    def test_admin_team_super_admin_assignment_requires_super_admin_context(self):
        organization_id = str(ObjectId())
        fake_db = FakeDB(
            admins=[
                {
                    '_id': ObjectId(),
                    'email': 'ops@tourapp.local',
                    'full_name': 'Ops Admin',
                    'role': 'moderator',
                    'is_active': True,
                }
            ]
        )
        admin_context = {
            'principal': {'_id': 'ops-1', 'email': 'ops@tourapp.local', 'full_name': 'Ops Admin', 'role': 'moderator'},
            'organization': {'_id': organization_id, 'name': 'Internal Admin Workspace', 'slug': 'internal-admin', 'organization_type': 'internal_admin', 'status': 'active'},
            'permissions': ['admin.team.manage'],
            'role_templates': [],
        }
        client = build_test_client(db=fake_db, admin_context=admin_context, current_admin=admin_context['principal'])

        with patched_database(fake_db):
            response = client.post(
                '/admin/team',
                json={
                    'full_name': 'New Super Admin',
                    'email': 'super@tourapp.local',
                    'phone': '+922222222222',
                    'password': 'Temporary123!',
                    'role_keys': ['platform_super_admin'],
                    'permission_overrides': {'allow': [], 'deny': []},
                    'scope_constraints': {},
                },
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn('Only a platform super admin can assign super admin access', response.json()['detail'])

    def test_admin_team_member_can_be_created_and_updated_by_super_admin(self):
        organization_id = str(ObjectId())
        fake_db = FakeDB()
        admin_context = {
            'principal': {'_id': 'super-1', 'email': 'super@tourapp.local', 'full_name': 'Super Admin', 'role': 'super_admin'},
            'organization': {'_id': organization_id, 'name': 'Internal Admin Workspace', 'slug': 'internal-admin', 'organization_type': 'internal_admin', 'status': 'active'},
            'permissions': ['platform.super_admin', 'admin.team.manage'],
            'role_templates': [],
        }
        client = build_test_client(db=fake_db, admin_context=admin_context, current_admin=admin_context['principal'])

        with patched_database(fake_db):
            create_response = client.post(
                '/admin/team',
                json={
                    'full_name': 'Finance Admin',
                    'email': 'finance@tourapp.local',
                    'phone': '+933333333333',
                    'password': 'Temporary123!',
                    'role_keys': ['admin_finance'],
                    'permission_overrides': {'allow': [], 'deny': []},
                    'scope_constraints': {},
                },
            )

            self.assertEqual(create_response.status_code, 201)
            created = create_response.json()['member']
            self.assertEqual(created['role_keys'], ['admin_finance'])
            self.assertIn('admin.billing.manage', created['permissions'])

            update_response = client.patch(
                f"/admin/team/{created['_id']}",
                json={'role_keys': ['admin_readonly'], 'membership_status': 'active'},
            )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()['member']
        self.assertEqual(updated['role_keys'], ['admin_readonly'])
        self.assertIn('admin.reports.read', updated['permissions'])
        self.assertEqual(fake_db.admins.docs[0]['role'], 'moderator')

    def test_operator_team_update_rejects_cross_org_membership(self):
        organization_id = str(ObjectId())
        different_org_id = str(ObjectId())
        membership_id = ObjectId()
        fake_db = FakeDB(
            organization_memberships=[
                {
                    '_id': membership_id,
                    'organization_id': different_org_id,
                    'principal_type': 'user',
                    'principal_id': str(ObjectId()),
                    'membership_status': 'active',
                    'role_keys': ['operator_sales'],
                    'permission_overrides': {'allow': [], 'deny': []},
                    'scope_constraints': {},
                }
            ]
        )
        operator_context = {
            'principal': {'_id': 'owner-1', 'email': 'owner@op.local', 'full_name': 'Owner'},
            'organization': {'_id': organization_id, 'name': 'Op Org', 'slug': 'op-org', 'organization_type': 'operator', 'status': 'active'},
            'permissions': ['operator.team.manage'],
            'role_templates': [],
        }
        client = build_test_client(db=fake_db, operator_context=operator_context)

        with patched_database(fake_db):
            update_response = client.patch(
                f"/operators/team/{membership_id}",
                json={'role_keys': ['operator_finance']},
            )

        self.assertEqual(update_response.status_code, 404)
        self.assertIn('Team member not found', update_response.json()['detail'])


if __name__ == '__main__':
    unittest.main()