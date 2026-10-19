import {useState,useEffect,createContext} from 'react'
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

// 表单受控绑定，这样子实现数据劫持
function Form(){
    const [input, setInput] = useState('')
    return (
        <div>
            <input type="text" value={input} onChange={(e)=>setInput(e.target.value)}/>
        </div>
    )
}

// React中获取DOM，需要使用useRef钩子
function GetDOM(){
    const input = useRef(null)
    return (
        <div>
            <input ref={input} type="text" />
            <button onClick={()=>console.log(input.current)}>获取输入框焦点</button>
        </div>
    )
}
// 使用context机制进行数据通信(跨层传递数据)
// 1. 使用creatContext方法创建一个上下文对象
const MsgContext = createContext()
// 2. 在顶层组件 通过Provider组件提供数据
function MsgProvider(){
    const msg = 'hello'
    return (
        <MsgContext.Provider value={{msg}}>
            <h1>hello</h1>
        </MsgContext.Provider>
    )
}
// 3. 在底层组件 通过useContext钩子获取数据
function MsgConsumer(){
    const {msg} = useContext(MsgContext)
    return (
        <div>
            <h1>{msg}</h1>
        </div>
    )
}

// useEffect Hook，这个钩子用于在组件挂载后执行一些副作用操作
function Use(){
    // 创建一个状态数据
    const [data,setData] = useState([])
    useEffect(()=>{
        async function getData(){
            const res = await fetch('https://www.baidu.com')
            const data = await res.json()
            console.log(data)
            setData(data)
        }
        getData()
    },[])
    return (
        <div>
            <h1>useEffect</h1>
        </div>
    )
}
/**1. 没有依赖项 初始 + 组件更新
 * 组件更新的时候也会调用useEffect函数
 * 2. 传入空数组  只在组件挂载时执行一次
 * 3. 传入特定的依赖项  初始 + 当依赖项发生变化时才会执行useEffect函数
 */
// 这useEffect是可以清楚副作用的，就是函数后添加上去一个return就可以了，eg清除定时器


/**封装自定义hook */
function useToogle(){
    // 可复用的逻辑代码
    const [value,setValue] = useState(false)
    const toogle = ()=>{setValue(!value)}
    return {
        value,
        toogle
    }
}
// 这个封装都是只要是可复用的逻辑和状态都可以进行封装成一个hook函数的

/**ReactHook的使用方式 
 * 1. 不能在组件外进行使用
 * 2. 不可以在循环中进行使用
 * 3. 只能在组件顶部进行使用
*/
// redux 状态管理工具
//1. 使用redux库
//2. 创建一个store对象
//3. 创建一个reducer函数
//4. 使用connect函数将组件与store连接起来
//5. 渲染组件
import {useSelector,useDispatch} from 'react-redux'
// 导入actionCreater函数
import {increment} from '../store/modules/counterStore'
import {fechChannelList} from '../store/modules/channelStore'
import {useEffect} from 'react'
function Counter(){
    const count = useSelector(state=>state.counter.count)
    const channelList = useSelector(state=>state.channel.list)
    const dispatch = useDispatch()
    useEffect(()=>{
        dispatch(fechChannelList())
    },[])
    console.log(channelList)
    return (
        <div>
            <button onClick={()=>dispatch(increment())}>增加</button>
            <h1>{count}</h1>
        </div>
    )
}

export { Num, Object,ClassStyle ,Use,Counter};
