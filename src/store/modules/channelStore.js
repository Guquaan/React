import {createSlice} from '@reduxjs/toolkit'
import axios from 'axios'
import {useDispatch} from 'react-redux'
const channelStore = createSlice({
    name:'channel',
    initialState:{
        list:[]
    },
    reducers:{
        setChannelList(state,action){
            state.list = action.payload
        }
    }
})

// 异步请求部分
const {setChannelList} = channelStore.actions

const fechChannelList = async () => {
    return async ()=>{
       const res =  await axios.get('http://geek.itheima.net/v1_0/channels')
    }
    dispatch(setChannelList(res.data.data.channels))
}

export {fechChannelList}

const reducer = channelStore.reducer
export default reducer