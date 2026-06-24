<template>
  <div class="team-page">
    <section class="team-hero">
      <div>
        <p class="eyebrow">Admin access control</p>
        <h1>Admin workspace memberships</h1>
        <p>Provision internal admins, assign section-specific roles, and update membership status without changing infrastructure.</p>
      </div>
      <div class="org-card" v-if="context">
        <span>Workspace</span>
        <strong>{{ context.organization.name }}</strong>
        <small>{{ context.organization.slug }}</small>
      </div>
    </section>

    <div v-if="notice" :class="['notice', noticeType]">{{ notice }}</div>

    <div class="team-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Admin members</p>
            <h2>Current scoped access</h2>
          </div>
          <button class="btn-secondary" type="button" @click="loadTeam" :disabled="loading">
            {{ loading ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>

        <div v-if="loading" class="empty-state">Loading team…</div>
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
              <select v-model="memberDrafts[member._id].role_keys" multiple size="5">
                <option v-for="role in roleTemplates" :key="role.key" :value="role.key">{{ role.name }}</option>
              </select>
            </label>
            <button class="btn-primary" type="button" @click="saveMember(member)">Save member</button>
          </article>
        </div>
      </section>

      <section class="panel form-panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Provision admin</p>
            <h2>Create or attach admin account</h2>
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
            Password
            <input v-model="form.password" type="text" placeholder="Required for new admin accounts" />
          </label>
          <label>
            Roles
            <select v-model="form.role_keys" multiple size="5">
              <option v-for="role in roleTemplates" :key="role.key" :value="role.key">{{ role.name }}</option>
            </select>
          </label>
          <button class="btn-primary" type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Add admin member' }}</button>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
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
const form = ref({
  full_name: '',
  email: '',
  phone: '',
  password: '',
  role_keys: ['admin_readonly'],
})

const humanize = (value) => String(value || '').replaceAll('_', ' ')

const resetForm = () => {
  form.value = {
    full_name: '',
    email: '',
    phone: '',
    password: '',
    role_keys: ['admin_readonly'],
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

const loadTeam = async () => {
  loading.value = true
  try {
    context.value = await accessStore.loadAdminContext(true)
    const response = await api.get('/admin/team')
    members.value = response.data.members || []
    roleTemplates.value = response.data.role_templates || []
    hydrateDrafts()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to load admin access data'
  } finally {
    loading.value = false
  }
}

const createMember = async () => {
  saving.value = true
  notice.value = ''
  try {
    const response = await api.post('/admin/team', form.value)
    noticeType.value = 'success'
    notice.value = response.data.created_account
      ? 'Admin account created and linked successfully.'
      : 'Existing admin account linked successfully.'
    resetForm()
    await loadTeam()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to provision admin member'
  } finally {
    saving.value = false
  }
}

const saveMember = async (member) => {
  notice.value = ''
  try {
    await api.patch(`/admin/team/${member._id}`, memberDrafts.value[member._id])
    noticeType.value = 'success'
    notice.value = 'Admin membership updated successfully.'
    await loadTeam()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to update admin membership'
  }
}

onMounted(loadTeam)
</script>

<style scoped>
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
  color: #1d4ed8;
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
  background: #dbeafe;
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
  background: #1d4ed8;
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