<template>
  <div class="container">
    <div class="tourist-dashboard">
      <h1>Tourist Dashboard</h1>
      
      <div class="dashboard-grid">
        <div class="card">
          <h3>My Bookings</h3>
          <p>View and manage your tour bookings</p>
          <router-link to="/my-bookings" class="btn btn-primary">
            View Bookings
          </router-link>
        </div>
        
        <div class="card">
          <h3>Search Tours</h3>
          <p>Find tour operators in your desired destination</p>
          <router-link to="/search" class="btn btn-primary">
            Search Tours
          </router-link>
        </div>
        
        <div class="card">
          <h3>Profile</h3>
          <p>Manage your profile and preferences</p>
          <button class="btn btn-primary">Edit Profile</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TouristDashboard',
  setup() {
    return {}
  }
}
</script>

<style scoped>
.tourist-dashboard h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.card h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.card p {
  margin-bottom: 1.5rem;
  color: #666;
}

.btn {
  padding: 0.5rem 1rem;
  text-decoration: none;
  display: inline-block;
}
</style>
