const emailDomain = 'tourlocal.com'

const makeEmail = (localPart) => `${localPart}@${emailDomain}`

export const adminBrandConfig = {
  appName: 'Tour Local',
  appUrl: 'https://tourlocal.com',
  browserTitle: 'Tour Local - Find Trusted Local Journeys',
  publicTagline: 'Local operator journeys',
  footerTagline: 'Find your perfect tour with local operators',
  supportEmail: makeEmail('support'),
  supportPhone: '+91-9876543210',
  loginEmailPlaceholder: makeEmail('admin'),
  logoAlt: 'Tour Local logo',
  portalTitle: 'Admin Portal',
  portalSubtitle: 'Tour Local Management System',
  consoleTitle: 'Admin Console',
  sidebarTitle: 'Control Center',
  sidebarDescription: 'Coordinate operators, traveler trust, reports, and platform operations from one place.',
  emails: {
    admin: makeEmail('admin'),
    finance: makeEmail('finance'),
    managers: makeEmail('managers'),
    team: makeEmail('team'),
  },
  sampleAdminUsers: [
    { name: 'Rajesh Kumar', email: makeEmail('rajesh'), role: 'admin' },
    { name: 'Priya Singh', email: makeEmail('priya'), role: 'manager' },
    { name: 'Amit Patel', email: makeEmail('amit'), role: 'supervisor' },
  ],
}

export { makeEmail }