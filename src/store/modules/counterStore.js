import {createSlice} from '@reduxjs/toolkit'

const counterStore = createSlice({
    name:'counter',
    // 初始化state
    initialState:{
        count:0
    },
    // 定义reducer函数 同步方法
    reducers:{
        increment(state){
            state.count++
        }
    },
    // 
})

// 解构出来actionCreater函数
const {increment} = counterStore.actions
// 获取reducer函数
const reducer = counterStore.reducer

// 以按需导出actionCreater函数
export {increment}
// 导出reducer函数
export default reducer
