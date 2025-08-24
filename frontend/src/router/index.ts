import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ScriptingDocsView from '../views/ScriptingDocsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/docs/scripting',
      name: 'scripting-docs',
      component: ScriptingDocsView,
    },
  ],
})

export default router
