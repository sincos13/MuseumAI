<script setup>
import { ref, onMounted } from 'vue'
import { MuseumPage } from '../design-system/components/index.js'
import { useHallDirectory } from '../composables/useHallDirectory.js'
import { useExhibits } from '../composables/useExhibits.js'
import ExhibitList from '../components/exhibits/ExhibitList.vue'
import FloorMap from '../components/layout/FloorMap.vue'

const { exhibits, loading, error, fetchExhibits } = useExhibits()

const { halls, fetchHalls, hallsLoading, hallsError } = useHallDirectory()
const selectedHall = ref('')
const selectedExhibit = ref(null)
const viewMode = ref('list')

onMounted(() => Promise.all([fetchHalls(), fetchExhibits()]))
</script>

<template>
  <MuseumPage class="exhibits-view">
    <h1>展品浏览</h1>
    <p>在地理坐标和图文资料之间切换，定位你想深入了解的展品。</p>

    <div class="exhibits-main">
      <el-alert v-if="error" :title="error" type="error" :closable="false" />
      <el-alert v-if="hallsError" :title="hallsError" type="warning" :closable="false">
        <el-button @click="fetchHalls">重试加载展厅</el-button>
      </el-alert>
      <el-select v-model="selectedHall" placeholder="全部展厅" clearable :loading="hallsLoading" aria-label="筛选展厅" @change="fetchExhibits(selectedHall ? { hall: selectedHall } : {})">
        <el-option v-for="hall in halls" :key="hall.slug" :label="hall.name" :value="hall.slug" />
      </el-select>
      <el-tabs v-model="viewMode" class="exhibits-tabs">
        <el-tab-pane label="列表视图" name="list">
          <ExhibitList :exhibits="exhibits" :loading="loading" @select="selectedExhibit = $event" />
        </el-tab-pane>

        <el-tab-pane label="地图视图" name="map">
          <FloorMap
            :exhibits="exhibits"
            :selected-exhibit="selectedExhibit"
            @select-exhibit="selectedExhibit = $event"
          />
        </el-tab-pane>
      </el-tabs>
    </div>
  </MuseumPage>
</template>

<style scoped>
.exhibits-view {
  height: 100%;
}

.exhibits-main {
  min-height: 520px;
}

.exhibits-tabs :deep(.el-tabs__content) {
  margin-top: 8px;
}

h1 {
  margin: 0;
  font-size: clamp(22px, 2.8vw, 30px);
  font-family: var(--font-family-base);
}

p {
  margin: 8px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
</style>
