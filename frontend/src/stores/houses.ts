import { defineStore } from 'pinia'
import {
  fetchHouses,
  createHouse,
  deleteHouse,
  createRoom,
  deleteRoom,
  type House,
  type HouseCreate,
  type CityTier
} from '../services/houses'

export const useHousesStore = defineStore('houses', {
  state: () => ({
    items: [] as House[],
    total: 0,
    loading: false,
    error: '',
    // Currently selected house's city tier, used to drive diagnosis price matching.
    activeCityTier: null as CityTier | null
  }),
  getters: {
    hasActiveHouse: (state) => state.items.length > 0
  },
  actions: {
    async fetchList() {
      this.loading = true
      this.error = ''
      try {
        const response = await fetchHouses()
        this.items = response.items
        this.total = response.total
        if (!this.activeCityTier && this.items.length > 0) {
          this.activeCityTier = this.items[0].city_tier
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : '房屋信息加载失败'
      } finally {
        this.loading = false
      }
    },
    async addHouse(payload: HouseCreate) {
      const house = await createHouse(payload)
      this.items = [house, ...this.items]
      this.total = this.items.length
      if (!this.activeCityTier) this.activeCityTier = house.city_tier
      return house
    },
    async removeHouse(id: string) {
      await deleteHouse(id)
      this.items = this.items.filter((item) => item.id !== id)
      this.total = this.items.length
      if (this.items.length === 0) this.activeCityTier = null
      else if (!this.items.some((item) => item.city_tier === this.activeCityTier)) {
        this.activeCityTier = this.items[0].city_tier
      }
    },
    async addRoom(houseId: string, roomName: string) {
      const room = await createRoom(houseId, roomName)
      this.items = this.items.map((house) =>
        house.id === houseId ? { ...house, rooms: [...house.rooms, room] } : house
      )
      return room
    },
    async removeRoom(houseId: string, roomId: string) {
      await deleteRoom(houseId, roomId)
      this.items = this.items.map((house) =>
        house.id === houseId ? { ...house, rooms: house.rooms.filter((r) => r.id !== roomId) } : house
      )
    },
    setActiveCityTier(tier: CityTier) {
      this.activeCityTier = tier
    }
  }
})
