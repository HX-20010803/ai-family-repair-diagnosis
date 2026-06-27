import { defineStore } from 'pinia'
import {
  fetchHouses,
  createHouse,
  deleteHouse,
  updateHouse,
  createRoom,
  deleteRoom,
  updateRoom,
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
    activeHouseId: '',
    // Currently selected house's city tier, used to drive diagnosis price matching.
    activeCityTier: null as CityTier | null
  }),
  getters: {
    hasActiveHouse: (state) => state.items.length > 0,
    activeHouse: (state) => state.items.find((house) => house.id === state.activeHouseId) || null
  },
  actions: {
    async fetchList() {
      this.loading = true
      this.error = ''
      try {
        const response = await fetchHouses()
        this.items = response.items
        this.total = response.total
        const activeStillExists = this.items.some((house) => house.id === this.activeHouseId)
        if (!activeStillExists && this.items.length > 0) {
          this.activeHouseId = this.items[0].id
          this.activeCityTier = this.items[0].city_tier
        }
        if (this.items.length === 0) {
          this.activeHouseId = ''
          this.activeCityTier = null
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
      if (!this.activeHouseId) {
        this.activeHouseId = house.id
        this.activeCityTier = house.city_tier
      }
      return house
    },
    async removeHouse(id: string) {
      await deleteHouse(id)
      this.items = this.items.filter((item) => item.id !== id)
      this.total = this.items.length
      if (this.items.length === 0) {
        this.activeHouseId = ''
        this.activeCityTier = null
      } else if (this.activeHouseId === id || !this.items.some((item) => item.id === this.activeHouseId)) {
        this.activeHouseId = this.items[0].id
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
    async editHouse(id: string, payload: Partial<HouseCreate>) {
      const updated = await updateHouse(id, payload)
      this.items = this.items.map((house) => (house.id === id ? updated : house))
      if (this.activeHouseId === id) {
        this.activeCityTier = updated.city_tier
      }
      return updated
    },
    async editRoom(houseId: string, roomId: string, roomName: string) {
      const updated = await updateRoom(houseId, roomId, roomName)
      this.items = this.items.map((house) =>
        house.id === houseId
          ? { ...house, rooms: house.rooms.map((r) => (r.id === roomId ? updated : r)) }
          : house
      )
      return updated
    },
    setActiveCityTier(tier: CityTier) {
      this.activeCityTier = tier
    },
    setActiveHouse(house: House) {
      this.activeHouseId = house.id
      this.activeCityTier = house.city_tier
    }
  }
})
