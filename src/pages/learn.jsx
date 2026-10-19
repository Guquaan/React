/** 原 React 学习笔记页面的容器（保留原有练习代码，不改动其内部实现） */
import { Num, Object as Obj, ClassStyle , Use,Counter} from './teach'
import List from './list'

export default function Learn({ mode }) {
  if (mode === 'list') {
    return (
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">📝 列表渲染练习</div>
            <div className="card__desc">原学习项目的评论列表 Demo，保留以记录学习过程</div>
          </div>
        </div>
        <div className="card__body">
          <List />
          
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card__head">
        <div>
          <div className="card__title">📘 React 基础练习</div>
          <div className="card__desc">数据定义、组件、列表遍历 —— 原学习项目的第一天成果</div>
        </div>
      </div>
      <div className="card__body">
        <Num />
        <Obj />
        <ClassStyle />
        <Counter />
      </div>
    </div>
  )
}
