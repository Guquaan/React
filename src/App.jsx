import { useState } from 'react'
import {Num,Object,ClassStyle} from './pages/teach'
import List from './pages/list'
import './App.css'

function App() {
  // 1. 定义组件
  const Button = ()=>{
    return <button>按钮</button>
  }
  return (
    <div>
      <List />
    </div>
  )
}

export default App
