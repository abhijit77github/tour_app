export function clearAdminSessionStorage(storage = localStorage) {
  storage.removeItem('adminToken')
  storage.removeItem('adminUser')
}

export function clearUserSessionStorage(storage = localStorage) {
  storage.removeItem('token')
}
