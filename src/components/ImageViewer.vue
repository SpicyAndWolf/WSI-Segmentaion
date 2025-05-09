<script setup>
defineProps({
  imageUrl: String,
  title: String,
});
</script>

<template>
  <div class="original-image">
    <h3>{{ title }}</h3>
    <img :src="imageUrl" class="image" />
  </div>
</template>

<style scoped>
.original-image {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image {
  max-width: 100%;
  height: auto;
}

h3 {
  margin-bottom: 10px;
  text-align: center;
}
</style>
