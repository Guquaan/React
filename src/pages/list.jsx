// 评论列表展示
import { useState } from 'react'
import './list.css'

// 初始评论数据
const initialComments = [
    {
        id: 1,
        name: '张三',
        avatar: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=avatar%20circle%20boy%20minimal&image_size=square_hd',
        content: '这个 React 教程讲得真的很清楚,useState 一看就懂了!',
        time: '2026-10-13 10:24',
        likes: 12
    },
    {
        id: 2,
        name: '李四',
        avatar: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=avatar%20circle%20girl%20minimal&image_size=square_hd',
        content: '请教一下,对象类型的状态更新时,是不是必须整体替换,不能直接改属性?',
        time: '2026-10-13 11:08',
        likes: 5
    },
    {
        id: 3,
        name: '王五',
        avatar: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=avatar%20circle%20cat%20minimal&image_size=square_hd',
        content: '同问楼上,我之前直接改属性视图没更新,后来才知道要 setObj({...obj, name: \'xxx\'})。',
        time: '2026-10-13 11:32',
        likes: 8
    }
]

// 高亮数据
const tabType = [
    {name:'new',title:'最新'},
    {name:'hot',title:'热评'}
]
function List(){
    // 评论数据
    const [comments, setComments] = useState(initialComments)
    // 新评论输入框内容
    const [input, setInput] = useState('')

    // 点赞:整体替换数组项,触发视图更新
    const handleLike = (id) => {
        setComments(comments.map(c =>
            c.id === id ? { ...c, likes: c.likes + 1 } : c
        ))
    }

    // 删除评论:filter 过滤掉指定 id,返回新数组触发视图更新
    const handleDelete = (id) => {
        setComments(comments.filter(c => c.id !== id))
    }

    // 发布评论:追加新评论到列表头部，直接使用结构赋值，触发视图更新
    const handleAdd = () => {
        const text = input.trim()
        if (!text) return
        const newComment = {
            id: Date.now(),
            name: '我',
            avatar: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=avatar%20circle%20me%20minimal&image_size=square_hd',
            content: text,
            time: new Date().toLocaleString('zh-CN'),
            likes: 0
        }
        setComments([newComment, ...comments])
        setInput('')
    }

    return (
        <div className="comment-list">
            {/**
             * 1. tab切换功能
             *  最新 / 热评
             * 切换的时候显示不一样的高亮
             * 2. 根据条件控制不一样的高亮效果
             */}
            <h1 className="comment-list__title">评论 ({comments.length})</h1>

            {/* 输入区 */}
            <div className="comment-input">
                <textarea
                    className="comment-input__field"
                    placeholder="说点什么吧..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
                <button className="comment-input__btn" onClick={handleAdd}>发布</button>
            </div>

            {/* 列表区 */}
            {comments.length === 0 ? (
                <p className="comment-empty">暂无评论,快来抢沙发~</p>
            ) : (
                <ul className="comment-items">
                    {comments.map(c => (
                        <li className="comment-item" key={c.id}>
                            <img className="comment-item__avatar" src={c.avatar} alt={c.name} />
                            <div className="comment-item__body">
                                <div className="comment-item__head">
                                    <span className="comment-item__name">{c.name}</span>
                                    <span className="comment-item__time">{c.time}</span>
                                </div>
                                <p className="comment-item__content">{c.content}</p>
                                <div className="comment-item__actions">
                                    <button
                                        className="comment-item__like"
                                        onClick={() => handleLike(c.id)}
                                    >
                                        ❤ {c.likes}
                                    </button>
                                    <button
                                        className="comment-item__delete"
                                        onClick={() => handleDelete(c.id)}
                                    >
                                        删除
                                    </button>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}

export default List
