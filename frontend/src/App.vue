<template>
  <div>

    <app-ui></app-ui>
    <app-ol></app-ol>

    </div>

</template>

<script>

import AppUI   from "./components/AppUI.vue";
import AppOL   from "./components/AppOL.vue";

export default {
  name: 'app',
  components: {
    'app-ui' : AppUI,
    'app-ol' : AppOL
  },

  data () {
    return {
        location  : null,

   }
  }
}

</script>

<style lang="scss">
</style>



