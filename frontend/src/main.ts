import App from '@/App.vue';
import { createPinia } from 'pinia';
import { createApp } from 'vue';

// Roboto font
import '@fontsource/roboto';
import '@fontsource/roboto-mono';

// Include Material icons
// Available icons: https://fonts.google.com/icons
// Use: Include the class 'material-icons' and make the inner text the icon name, i.e.
//		<span class="material-icons">my_icon</span>
// Icon size can be adjusted with 'font-size' and color can be adjusted with 'color'
import 'material-icons/iconfont/material-icons.css';

// Setup App
const app = createApp(App);
app.use(createPinia());
app.mount('#app');
