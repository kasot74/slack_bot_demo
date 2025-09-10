// 创建一个函数来调用聊天接口
async function chatWithAI(messages) {
    try {
      // 构建请求体
      const requestBody = {
        //model: 'nalang-v17-2',//turbo-17
        //model: 'nalang-turbo-v19',
        //model: 'nalang-turbo-v18',
        //model: 'nalang-xl-16k',
        model: 'nalang-xl-10',
        messages: messages,
        stream: true,
        temperature: 0.7,
        max_tokens: 800,
        top_p: 0.35,
        repetition_penalty: 1.05
      };

      // 修正API地址
      const response = await fetch('https://www.gpt4novel.com/api/xiaoshuoai/ext/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',       
          'Authorization': 'Bearer <换成你自己的API>'
        },
        body: JSON.stringify(requestBody)
      });
      
      // 检查响应状态
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 使用response.body作为流
      const stream = response.body;
      const decoder = new TextDecoder();
      let buffer = '';

      // 设置数据处理函数   
      stream.on('data', chunk => {
        // 解码数据并添加到缓冲区
        buffer += decoder.decode(chunk, { stream: true });

        // 处理缓冲区中的完整行
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          if (line.startsWith('data: ')) {
            try {
              const jsonData = JSON.parse(line.slice(6).trim());
              
              // 处理完成事件
              if (jsonData.completed) {
                console.log('Stream completed:', jsonData.completed);
                return;
              }
              
              // 处理普通的内容块
              if (jsonData.choices?.[0]?.delta?.content) {
                const content = jsonData.choices[0].delta.content;
                process.stdout.write(content);
              }
            } catch (e) {
              // 忽略空行导致的解析错误
              if (line.trim()) {
                console.error('Error parsing JSON:', e);
              }
            }
          }
        }
      });

      // 处理流结束
      stream.on('end', () => {
        // 处理最后可能剩余的数据
        if (buffer.trim()) {
          const line = buffer.trim();
          if (line.startsWith('data: ')) {
            try {
              const jsonData = JSON.parse(line.slice(6).trim());
              if (jsonData.choices?.[0]?.delta?.content) {
                process.stdout.write(jsonData.choices[0].delta.content);
              }
            } catch (e) {
              if (line.trim()) {
                console.error('Error parsing JSON:', e);
              }
            }
          }
        }
      });

      // 处理错误
      stream.on('error', error => {
        console.error('Stream error:', error);
      });

    } catch (error) {
      console.error('Error:', error);
    }
}

// 使用示例
const messages = [
    {
      role: 'system',
      content: '你是一个有帮助的AI助手。'
    },
    {
      role: 'user',
      content: '你好,请介绍一下自己。'
    }
];

// 使用node-fetch
import('node-fetch').then(({ default: fetch }) => {
    global.fetch = fetch;
    chatWithAI(messages);
}).catch(err => {
    console.error('请先安装 node-fetch:', err);
    console.log('运行 npm install node-fetch 来安装');
}); 