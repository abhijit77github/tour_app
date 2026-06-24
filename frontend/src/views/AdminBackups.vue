<template>
  <div class="admin-backups">
    <div class="page-header">
      <div>
        <h1>Backups & Restore</h1>
        <p class="subtitle">Super-admin-only database protection with local archive and S3 workflows.</p>
      </div>
      <button class="refresh-button" @click="refreshAll" :disabled="loadingJobs || loadingCapabilities">
        {{ loadingJobs || loadingCapabilities ? 'Refreshing...' : 'Refresh' }}
      </button>
    </div>

    <div v-if="!canManage" class="access-card">
      <h2>Access restricted</h2>
      <p>Only platform super admins can create backups or run restore jobs.</p>
    </div>

    <template v-else>
      <div class="capability-grid">
        <div class="capability-card">
          <div class="card-label">Local backup</div>
          <div class="card-value">{{ capabilities.local?.enabled ? 'Ready' : 'Unavailable' }}</div>
          <p>{{ capabilities.local?.directory || 'No directory configured' }}</p>
        </div>
        <div class="capability-card">
          <div class="card-label">S3 backup</div>
          <div class="card-value">{{ capabilities.s3?.enabled ? 'Configured' : 'Not configured' }}</div>
          <p>{{ capabilities.s3?.bucket || 'Set BACKUP_S3_BUCKET to enable S3 backups.' }}</p>
        </div>
        <div class="capability-card warning" :class="{ ok: capabilities.tools?.mongodump && capabilities.tools?.mongorestore }">
          <div class="card-label">Mongo tools</div>
          <div class="card-value">{{ capabilities.tools?.mongodump && capabilities.tools?.mongorestore ? 'Installed' : 'Missing' }}</div>
          <p>
            Dump: {{ capabilities.tools?.mongodump || 'not found' }}
            <br />
            Restore: {{ capabilities.tools?.mongorestore || 'not found' }}
          </p>
        </div>
      </div>

      <div v-if="globalError" class="feedback error">{{ globalError }}</div>
      <div v-if="successMessage" class="feedback success">{{ successMessage }}</div>

      <div class="workspace-grid">
        <section class="panel create-panel">
          <div class="panel-header">
            <h2>Create backup</h2>
            <span class="pill">Queued job</span>
          </div>
          <label class="field">
            <span>Destination</span>
            <select v-model="createForm.destination">
              <option value="local">Local archive</option>
              <option value="s3" :disabled="!capabilities.s3?.enabled">S3 object storage</option>
            </select>
          </label>
          <label class="field">
            <span>Label</span>
            <input v-model="createForm.label" type="text" maxlength="80" placeholder="Release cutover, weekly snapshot, pre-migration" />
          </label>
          <button class="primary-button" @click="createBackup" :disabled="submittingBackup">
            {{ submittingBackup ? 'Queueing...' : 'Queue backup' }}
          </button>
          <p class="hint">The archive is created with `mongodump --archive --gzip`. Restore jobs require the backup code for confirmation.</p>
        </section>

        <section class="panel list-panel">
          <div class="panel-header list-header">
            <div>
              <h2>Backup jobs</h2>
              <p class="meta-copy">Track backup and restore execution, download local archives, and initiate controlled restores.</p>
            </div>
            <div class="toolbar">
              <select v-model="filters.jobType">
                <option value="">All jobs</option>
                <option value="backup">Backup jobs</option>
                <option value="restore">Restore jobs</option>
              </select>
            </div>
          </div>

          <div v-if="loadingJobs" class="empty-state">Loading backup jobs...</div>
          <div v-else-if="!jobs.length" class="empty-state">No backup or restore jobs yet.</div>
          <div v-else class="job-list">
            <article v-for="job in jobs" :key="job._id" class="job-card">
              <div class="job-topline">
                <div>
                  <h3>{{ job.job_code }}</h3>
                  <p>{{ formatDate(job.created_at) }}</p>
                </div>
                <div class="status-row">
                  <button
                    class="ghost-button status-refresh-button"
                    @click="refreshJobStatus(job)"
                    :disabled="jobRefreshBusy[job._id]"
                  >
                    {{ jobRefreshBusy[job._id] ? 'Refreshing...' : 'Refresh status' }}
                  </button>
                  <span class="job-kind">{{ job.job_type }}</span>
                  <span class="status-pill" :class="job.status">{{ job.status }}</span>
                </div>
              </div>

              <div class="job-meta">
                <span v-if="job.destination">Destination: {{ job.destination }}</span>
                <span v-if="job.source">Restore source: {{ job.source }}</span>
                <span v-if="job.label">Label: {{ job.label }}</span>
                <span v-if="job.created_by?.email">By: {{ job.created_by.email }}</span>
                <span v-if="job.artifact?.size_bytes">Size: {{ formatBytes(job.artifact.size_bytes) }}</span>
                <span v-if="job.source_backup_id">Source backup linked</span>
              </div>

              <div v-if="job.error_message" class="job-error">{{ job.error_message }}</div>

              <div v-if="job.job_type === 'backup' && job.status === 'completed'" class="restore-box">
                <label class="field compact-field">
                  <span>Confirmation code</span>
                  <input
                    v-model="restoreForm(job)._confirmationCode"
                    type="text"
                    :placeholder="`Type ${job.job_code}`"
                  />
                </label>
                <label class="checkbox-row">
                  <input v-model="restoreForm(job).dropExisting" type="checkbox" />
                  <span>Drop existing collections during restore</span>
                </label>
                <div class="action-row">
                  <button
                    v-if="job.artifact?.local_path"
                    class="secondary-button"
                    @click="queueRestore(job, 'local')"
                    :disabled="restoreBusy[job._id]"
                  >
                    Restore Local
                  </button>
                  <button
                    v-if="job.artifact?.s3_key"
                    class="secondary-button"
                    @click="queueRestore(job, 's3')"
                    :disabled="restoreBusy[job._id]"
                  >
                    Restore S3
                  </button>
                  <button
                    v-if="job.artifact?.local_path"
                    class="ghost-button"
                    @click="downloadLocalBackup(job)"
                    :disabled="downloadBusy[job._id]"
                  >
                    Download
                  </button>
                </div>
              </div>
            </article>
          </div>

          <div class="pagination-row">
            <button class="ghost-button" @click="changePage(-1)" :disabled="pagination.page <= 1 || loadingJobs">Previous</button>
            <span>Page {{ pagination.page }} of {{ pagination.pages }}</span>
            <button class="ghost-button" @click="changePage(1)" :disabled="pagination.page >= pagination.pages || loadingJobs">Next</button>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

import api from '../services/api'
import { useAccessStore } from '../stores/access'

const accessStore = useAccessStore()

const loadingCapabilities = ref(false)
const loadingJobs = ref(false)
const submittingBackup = ref(false)
const capabilities = ref({
  local: {},
  s3: {},
  tools: {},
})
const jobs = ref([])
const pagination = ref({
  page: 1,
  page_size: 10,
  total: 0,
  pages: 1,
})
const createForm = reactive({
  destination: 'local',
  label: '',
})
const filters = reactive({
  jobType: '',
})
const restoreForms = reactive({})
const restoreBusy = reactive({})
const downloadBusy = reactive({})
const jobRefreshBusy = reactive({})
const globalError = ref('')
const successMessage = ref('')

const canManage = computed(() => accessStore.hasAdminPermission('admin.backups.manage'))

const formatDate = (value) => {
  if (!value) return 'Unknown time'
  return new Date(value).toLocaleString()
}

const formatBytes = (value) => {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

const clearFeedback = () => {
  globalError.value = ''
  successMessage.value = ''
}

const replaceJobInList = (jobRecord) => {
  const currentJobs = [...jobs.value]
  const targetIndex = currentJobs.findIndex((job) => job._id === jobRecord._id)
  if (targetIndex === -1) return
  currentJobs.splice(targetIndex, 1, jobRecord)
  jobs.value = currentJobs
}

const restoreForm = (job) => {
  if (!restoreForms[job._id]) {
    restoreForms[job._id] = {
      _confirmationCode: '',
      dropExisting: false,
    }
  }
  return restoreForms[job._id]
}

const loadCapabilities = async () => {
  if (!canManage.value) return
  loadingCapabilities.value = true
  try {
    const response = await api.get('/admin/backups/capabilities')
    capabilities.value = response.data
    if (!capabilities.value.s3?.enabled && createForm.destination === 's3') {
      createForm.destination = 'local'
    }
  } catch (error) {
    globalError.value = error.response?.data?.detail || 'Failed to load backup capabilities.'
  } finally {
    loadingCapabilities.value = false
  }
}

const loadJobs = async () => {
  if (!canManage.value) return
  loadingJobs.value = true
  try {
    const response = await api.get('/admin/backups/jobs', {
      params: {
        page: pagination.value.page,
        page_size: pagination.value.page_size,
        job_type: filters.jobType || undefined,
      },
    })
    jobs.value = response.data.items || []
    pagination.value = {
      ...pagination.value,
      ...(response.data.pagination || {}),
    }
  } catch (error) {
    globalError.value = error.response?.data?.detail || 'Failed to load backup jobs.'
  } finally {
    loadingJobs.value = false
  }
}

const refreshAll = async () => {
  clearFeedback()
  await Promise.all([loadCapabilities(), loadJobs()])
}

const refreshJobStatus = async (job) => {
  clearFeedback()
  jobRefreshBusy[job._id] = true
  try {
    const response = await api.get(`/admin/backups/jobs/${job._id}`)
    replaceJobInList(response.data)
  } catch (error) {
    globalError.value = error.response?.data?.detail || `Failed to refresh status for ${job.job_code}.`
  } finally {
    jobRefreshBusy[job._id] = false
  }
}

const createBackup = async () => {
  clearFeedback()
  submittingBackup.value = true
  try {
    const response = await api.post('/admin/backups/jobs', {
      destination: createForm.destination,
      label: createForm.label || null,
    })
    successMessage.value = `Backup job ${response.data.job_code} queued.`
    createForm.label = ''
    pagination.value.page = 1
    await loadJobs()
  } catch (error) {
    globalError.value = error.response?.data?.detail || 'Failed to queue backup job.'
  } finally {
    submittingBackup.value = false
  }
}

const queueRestore = async (job, source) => {
  clearFeedback()
  const form = restoreForm(job)
  restoreBusy[job._id] = true
  try {
    const response = await api.post(`/admin/backups/jobs/${job._id}/restore`, {
      source,
      confirmation_code: form._confirmationCode,
      drop_existing_data: form.dropExisting,
    })
    successMessage.value = `Restore job ${response.data.job_code} queued from ${job.job_code}.`
    form._confirmationCode = ''
    form.dropExisting = false
    pagination.value.page = 1
    await loadJobs()
  } catch (error) {
    globalError.value = error.response?.data?.detail || 'Failed to queue restore job.'
  } finally {
    restoreBusy[job._id] = false
  }
}

const downloadLocalBackup = async (job) => {
  clearFeedback()
  downloadBusy[job._id] = true
  try {
    const response = await api.get(`/admin/backups/jobs/${job._id}/download`, {
      responseType: 'blob',
    })
    const objectUrl = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = job.artifact?.file_name || `${job.job_code}.archive.gz`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(objectUrl)
  } catch (error) {
    globalError.value = error.response?.data?.detail || 'Failed to download local backup.'
  } finally {
    downloadBusy[job._id] = false
  }
}

const changePage = async (offset) => {
  const nextPage = pagination.value.page + offset
  if (nextPage < 1 || nextPage > pagination.value.pages) return
  pagination.value.page = nextPage
  await loadJobs()
}

watch(
  () => filters.jobType,
  async () => {
    pagination.value.page = 1
    await loadJobs()
  }
)

onMounted(async () => {
  await accessStore.loadAdminContext()
  if (!canManage.value) return
  await refreshAll()
})
</script>

<style scoped>
.admin-backups {
  display: grid;
  gap: 1.5rem;
}

.page-header,
.panel-header,
.job-topline,
.action-row,
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.page-header {
  align-items: flex-start;
}

.page-header h1,
.panel-header h2,
.job-topline h3 {
  margin: 0;
}

.subtitle,
.meta-copy,
.hint,
.job-topline p,
.capability-card p,
.access-card p {
  margin: 0.35rem 0 0;
  color: #64748b;
}

.capability-grid,
.workspace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.workspace-grid {
  align-items: start;
}

.panel,
.capability-card,
.access-card,
.job-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
}

.capability-card,
.access-card,
.job-card {
  padding: 1.1rem 1.2rem;
}

.panel {
  padding: 1.3rem;
}

.create-panel {
  min-width: 0;
}

.list-panel {
  grid-column: span 2;
}

.card-label,
.job-kind,
.pill {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  font-weight: 700;
  color: #92400e;
}

.card-value {
  margin-top: 0.45rem;
  font-size: 1.4rem;
  font-weight: 700;
  color: #0f172a;
}

.warning {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
}

.warning.ok {
  background: linear-gradient(180deg, #ecfdf5 0%, #ffffff 100%);
}

.field {
  display: grid;
  gap: 0.45rem;
  margin-top: 1rem;
}

.field span,
.checkbox-row span {
  font-weight: 600;
  color: #334155;
}

.field input,
.field select {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
  font: inherit;
  background: #fff;
}

.compact-field {
  margin-top: 0;
}

.feedback {
  border-radius: 14px;
  padding: 0.9rem 1rem;
  font-weight: 600;
}

.feedback.error,
.job-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.feedback.success {
  background: #ecfdf5;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.job-list {
  display: grid;
  gap: 0.9rem;
  margin-top: 1rem;
}

.job-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.8rem;
}

.job-meta span {
  padding: 0.42rem 0.65rem;
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-size: 0.84rem;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.status-refresh-button {
  padding: 0.45rem 0.7rem;
  font-size: 0.78rem;
}

.status-pill,
.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
}

.pill {
  background: #fff7ed;
  color: #9a3412;
}

.status-pill.queued {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-pill.running {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.completed {
  background: #dcfce7;
  color: #166534;
}

.status-pill.failed {
  background: #fee2e2;
  color: #b91c1c;
}

.restore-box {
  margin-top: 1rem;
  display: grid;
  gap: 0.8rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.toolbar select,
.refresh-button,
.primary-button,
.secondary-button,
.ghost-button {
  border-radius: 12px;
  font: inherit;
  font-weight: 700;
}

.refresh-button,
.ghost-button {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
  padding: 0.75rem 0.95rem;
}

.toolbar select {
  border: 1px solid #cbd5e1;
  background: #fff;
  padding: 0.7rem 0.85rem;
}

.primary-button,
.secondary-button {
  border: none;
  padding: 0.8rem 1rem;
  color: #fff;
}

.primary-button {
  margin-top: 1rem;
  background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
}

.secondary-button {
  background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
}

.empty-state,
.pagination-row {
  margin-top: 1rem;
}

.empty-state {
  padding: 1.25rem;
  border-radius: 14px;
  background: #f8fafc;
  color: #64748b;
}

button:disabled,
select:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .list-panel {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .page-header,
  .panel-header,
  .job-topline,
  .action-row,
  .pagination-row {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar select,
  .refresh-button,
  .primary-button,
  .secondary-button,
  .ghost-button {
    width: 100%;
  }
}
</style>