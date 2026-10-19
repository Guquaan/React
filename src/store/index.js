import {configureStore} from '@reduxjs/toolkit'
// 导入子模块reducer
import counterReducer from './modules/counterStore'
import channelReducer from './modules/channelStore'
const store = configureStore({
    reducer:{
        counter:counterReducer,
        channel:channelReducer
    }
})

// 导出store对象
export default store
