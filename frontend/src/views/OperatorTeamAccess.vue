<template>
  <div class="team-page">
    <section class="team-hero">
      <div>
        <p class="eyebrow">Operator access control</p>
        <h1>Team members and scoped access</h1>
        <p>Manage who can access profile, billing, quotes, itineraries, and promotions inside your operator organization.</p>
      </div>
      <div class="org-card" v-if="context">
        <span>Organization</span>
        <strong>{{ context.organization.name }}</strong>
        <small>{{ context.organization.slug }}</small>
      </div>
    </section>

    <div v-if="notice" :class="['notice', noticeType]">{{ notice }}</div>

    <div class="team-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Current team</p>
            <h2>Active memberships</h2>
          </div>
          <button class="btn-secondary" type="button" @click="loadTeam" :disabled="loading">
            {{ loading ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>

        <div v-if="loading" class="empty-state">Loading team…</div>
        <div v-else-if="!members.length" class="empty-state">No team members yet.</div>
        <div v-else class="member-list">
          <article v-for="member in members" :key="member._id" class="member-card">
            <div>
              <h3>{{ member.principal?.full_name || member.principal?.email }}</h3>
              <p>{{ member.principal?.email }}</p>
              <small>{{ member.membership_status }}</small>
            </div>
            <div class="pill-row">
              <span v-for="roleKey in member.role_keys" :key="roleKey" class="pill">{{ humanize(roleKey) }}</span>
            </div>
            <label>
              Status
              <select v-model="memberDrafts[member._id].membership_status">
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
                <option value="revoked">Revoked</option>
              </select>
            </label>
            <label>
              Roles
              <select v-model="memberDrafts[member._id].role_keys" multiple size="4">
                <option v-for="role in roleTemplates" :key="role.key" :value="role.key">{{ role.name }}</option>
              </select>
            </label>
            <button class="btn-primary" type="button" @click="saveMember(member)">Save member</button>
          </article>
        </div>
        <div class="pager-row">
          <span class="pager-copy">{{ memberRangeLabel }}</span>
          <div class="pager-controls">
            <button class="btn-secondary" type="button" @click="previousPage" :disabled="currentPage === 1 || loading">Prev</button>
            <span>Page {{ currentPage }} / {{ totalPages }}</span>
            <button class="btn-secondary" type="button" @click="nextPage" :disabled="!memberPagination.hasMore || loading">Next</button>
          </div>
        </div>
      </section>

      <section class="panel form-panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Provision access</p>
            <h2>Add or attach team member</h2>
          </div>
        </div>

        <form class="member-form" @submit.prevent="createMember">
          <label>
            Full name
            <input v-model="form.full_name" type="text" required />
          </label>
          <label>
            Email
            <input v-model="form.email" type="email" required />
          </label>
          <label>
            Phone
            <input v-model="form.phone" type="text" />
          </label>
          <label>
            Temporary password
            <input v-model="form.password" type="text" placeholder="Required for new accounts" />
          </label>
          <label>
            Roles
            <select v-model="form.role_keys" multiple size="5">
              <option v-for="role in roleTemplates" :key="role.key" :value="role.key">{{ role.name }}</option>
            </select>
          </label>
          <button class="btn-primary" type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Add team member' }}</button>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'
import { useAccessStore } from '../stores/access'

const accessStore = useAccessStore()
const context = ref(null)
const members = ref([])
const roleTemplates = ref([])
const memberDrafts = ref({})
const loading = ref(false)
const saving = ref(false)
const notice = ref('')
const noticeType = ref('success')
const currentPage = ref(1)
const pageCursors = ref([null])
const PAGE_SIZE = 8
const memberPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const form = ref({
  full_name: '',
  email: '',
  phone: '',
  password: '',
  role_keys: ['operator_manager'],
})
const totalPages = computed(() => Math.max(1, Math.ceil((memberPagination.value.totalItems || 0) / PAGE_SIZE)))
const memberRangeLabel = computed(() => {
  const totalItems = memberPagination.value.totalItems || 0
  if (!totalItems || !members.value.length) return '0-0 of 0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = start + members.value.length - 1
  return `${start}-${end} of ${totalItems}`
})

const humanize = (value) => String(value || '').replaceAll('_', ' ')

const resetForm = () => {
  form.value = {
    full_name: '',
    email: '',
    phone: '',
    password: '',
    role_keys: ['operator_manager'],
  }
}

const hydrateDrafts = () => {
  memberDrafts.value = members.value.reduce((acc, member) => {
    acc[member._id] = {
      membership_status: member.membership_status,
      role_keys: [...member.role_keys],
    }
    return acc
  }, {})
}

const resetPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const loadTeam = async (page = currentPage.value) => {
  loading.value = true
  try {
    context.value = await accessStore.loadOperatorContext(true)
    const params = { page_size: PAGE_SIZE }
    const currentCursor = pageCursors.value[page - 1]
    if (currentCursor) params.cursor = currentCursor
    const response = await api.get('/operators/team', { params })
    members.value = response.data.members || []
    roleTemplates.value = response.data.role_templates || []
    memberPagination.value = {
      totalItems: response.data.pagination?.total_items || members.value.length,
      hasMore: Boolean(response.data.pagination?.has_more),
      nextCursor: response.data.pagination?.next_cursor || null,
    }
    if (pageCursors.value.length === page) {
      pageCursors.value.push(memberPagination.value.nextCursor)
    } else {
      pageCursors.value[page] = memberPagination.value.nextCursor
    }
    pageCursors.value = pageCursors.value.slice(0, page + 1)
    currentPage.value = page
    hydrateDrafts()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to load team access data'
  } finally {
    loading.value = false
  }
}

const createMember = async () => {
  saving.value = true
  notice.value = ''
  try {
    const response = await api.post('/operators/team', form.value)
    noticeType.value = 'success'
    notice.value = response.data.created_account
      ? 'Team member account created and linked successfully.'
      : 'Existing operator account linked to the organization successfully.'
    resetForm()
    resetPagination()
    await loadTeam(1)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to add team member'
  } finally {
    saving.value = false
  }
}

const saveMember = async (member) => {
  notice.value = ''
  try {
    await api.patch(`/operators/team/${member._id}`, memberDrafts.value[member._id])
    noticeType.value = 'success'
    notice.value = 'Team member updated successfully.'
    await loadTeam(currentPage.value)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to update team member'
  }
}

const previousPage = async () => {
  if (currentPage.value === 1 || loading.value) return
  await loadTeam(currentPage.value - 1)
}

const nextPage = async () => {
  if (!memberPagination.value.hasMore || loading.value) return
  await loadTeam(currentPage.value + 1)
}

onMounted(() => {
  resetPagination()
  loadTeam(1)
})
</script>

<style scoped>
.pager-row {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.pager-copy {
  color: #64748b;
  font-size: 0.88rem;
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.team-page {
  padding: 2rem;
}

.team-hero {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.eyebrow, .panel-kicker {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #0f766e;
  font-weight: 700;
  font-size: 0.78rem;
}

.org-card, .panel {
  background: #fff;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  padding: 1rem 1.1rem;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.team-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 1rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.member-list {
  display: grid;
  gap: 1rem;
}

.member-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
  display: grid;
  gap: 0.75rem;
}

.pill-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.pill {
  padding: 0.2rem 0.55rem;
  background: #e0f2fe;
  border-radius: 999px;
  font-size: 0.78rem;
}

.member-form, label {
  display: grid;
  gap: 0.4rem;
}

.member-form {
  gap: 0.9rem;
}

input, select {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
}

.btn-primary, .btn-secondary {
  border: none;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-weight: 700;
}

.btn-primary {
  background: #0f766e;
  color: #fff;
}

.btn-secondary {
  background: #e2e8f0;
  color: #0f172a;
}

.notice {
  margin-bottom: 1rem;
  padding: 0.8rem 1rem;
  border-radius: 12px;
}

.notice.success {
  background: #dcfce7;
  color: #166534;
}

.notice.error {
  background: #fee2e2;
  color: #991b1b;
}

.empty-state {
  padding: 1rem;
  color: #64748b;
}

@media (max-width: 900px) {
  .team-grid {
    grid-template-columns: 1fr;
  }

  .team-hero {
    flex-direction: column;
  }
}
</style>