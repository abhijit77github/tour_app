import { h, render } from 'vue'
import Toast from '../components/Toast.vue'

let toastContainer = null
let toastId = 0

function ensureContainer() {
  if (!toastContainer) {
    toastContainer = document.createElement('div')
    toastContainer.id = 'toast-container'
    document.body.appendChild(toastContainer)
  }
  return toastContainer
}

function createToast(options) {
  const container = ensureContainer()
  const id = `toast-${toastId++}`
  
  const wrapper = document.createElement('div')
  wrapper.id = id
  container.appendChild(wrapper)
  
  const vnode = h(Toast, {
    ...options,
    onClose: () => {
      render(null, wrapper)
      container.removeChild(wrapper)
    }
  })
  
  render(vnode, wrapper)
}

export function useToast() {
  return {
    success: (message, title = '', duration = 3000) => {
      createToast({ type: 'success', message, title, duration })
    },
    error: (message, title = '', duration = 4000) => {
      createToast({ type: 'error', message, title, duration })
    },
    warning: (message, title = '', duration = 3500) => {
      createToast({ type: 'warning', message, title, duration })
    },
    info: (message, title = '', duration = 3000) => {
      createToast({ type: 'info', message, title, duration })
    }
  }
}
