<template>
  <footer class="footer">
    <div class="container">
      <p>&copy; 2026 {{ adminBrand.appName }}. All rights reserved.</p>
      <p>{{ adminBrand.footerTagline }}</p>
    </div>
  </footer>
</template>

<script>
import { adminBrandConfig } from '../config/adminBrand'

export default {
  name: 'Footer',
  setup() {
    return {
      adminBrand: adminBrandConfig,
    }
  }
}
</script>

<style scoped>
.footer {
  background: #2c3e50;
  color: white;
  padding: 2rem 0;
  text-align: center;
  margin-top: 3rem;
}

.footer p {
  margin: 0.5rem 0;
}
</style>
