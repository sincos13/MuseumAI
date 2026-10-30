<script setup>
import { ref } from 'vue'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'

defineProps({
  loading: Boolean
})

const emit = defineEmits(['plan'])

const availableTime = ref(60)
const selectedInterests = ref([])

const { categories: interestOptions } = useMuseumProfile()

function handleSubmit() {
  emit('plan', {
    availableTime: availableTime.value,
    interests: selectedInterests.value
  })
}
</script>

<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>规划您的导览路线</span>
      </div>
    </template>

    <el-form label-position="top">
      <el-form-item label="可用时间（分钟）">
        <el-slider
          v-model="availableTime"
          :min="30"
          :max="180"
          :step="15"
          show-stops
          show-input
        />
      </el-form-item>

      <el-form-item label="感兴趣的类别">
        <el-checkbox-group v-model="selectedInterests">
          <el-checkbox
            v-for="opt in interestOptions"
            :key="opt.value"
            :label="opt.value"
          >
            {{ opt.label }}
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <el-button
        type="primary"
        :loading="loading"
        :disabled="selectedInterests.length === 0"
        @click="handleSubmit"
      >
        生成路线
      </el-button>
    </el-form>
  </el-card>
</template>

<style scoped>
.card-header {
  font-weight: 500;
}
</style>
