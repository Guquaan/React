import {useState} from 'react'
import './teach.css'

/** 
 * 注意：useState需要配套使用，不能进行分布使用，否则出现视图不更新的现象
 * 
 */
function Num(){
    // 1. 第一个参数是初始值，第二个参数是更新函数
    const [count, setCount] = useState(0)

    // 2. 定义点击事件
    const handleclick = ()=>{
        setCount(count+1)
    }
    return (
        <div>
            <h1 onClick={handleclick}>{count}</h1>
        </div>
    )
}

function Object(){
    // 修改对象类型
    const [obj, setObj] = useState({
        name:'张三',
        age:18
    })
    const changeObj = ()=>{
        setObj({
            name:'李四',
            age:20
        })
    }
    return (
        <div>
            <h1 onClick={changeObj}>{obj.name}</h1>
            <h2 onClick={changeObj}>{obj.age}</h2>
        </div>
    )
    // 鉴于对象类型应该是直接传入一个新的对象数据
}


/**  组件样式改变 */
function ClassStyle(){
    const style = {
        color:'red'
    }
    return (
        <div>
            {/** 行内组件样式 */}
            <h1 style={{color:'red'}}>行内组件样式</h1>
            {/** 类组件样式 */}
            <h1 style={style}>类组件样式</h1>
            {/** 导入组件样式 */}
            <h1 className='counter'>导入组件样式</h1>
        </div>
    )
}

export { Num, Object,ClassStyle };
