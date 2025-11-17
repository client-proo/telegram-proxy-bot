export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // هندل کردن درخواست‌های پروکسی
    if (path === '/proxy') {
      return handleProxyRequest(request);
    }

    // هندل کردن وب‌هوک تلگرام
    if (request.method === 'POST' && path === '/') {
      return handleTelegramUpdate(request, env);
    }

    // هندل کردن درخواست‌های GET
    if (request.method === 'GET') {
      if (path === '/setWebhook') {
        return setWebhook(env);
      }
      if (path === '/health') {
        return new Response('OK');
      }
      return new Response('Telegram Proxy Bot is Running!');
    }

    return new Response('Not Found', { status: 404 });
  }
}

async function handleTelegramUpdate(request, env) {
  try {
    const update = await request.json();
    
    if (update.message && update.message.text) {
      await handleMessage(update.message, env);
    }
    
    return new Response('OK');
  } catch (error) {
    console.error('Error handling update:', error);
    return new Response('Error', { status: 500 });
  }
}

async function handleMessage(message, env) {
  const chatId = message.chat.id;
  const text = message.text.trim();

  if (text === '/start') {
    await sendMessage(env, chatId, 
      `🤖 **ربات پروکسی ساز حرفه‌ای**\n\n` +
      `لینک مستقیم فایل خود را ارسال کنید تا لینک پروکسی شده آن را دریافت کنید.\n\n` +
      `⚡ **ویژگی‌ها:**\n` +
      `• پشتیبانی از فایل‌های بزرگ\n` +
      `• قابلیت ادامه دانلود\n` +
      `• سرعت بالا\n` +
      `• نیم بها برای کاربران ایرانی\n\n` +
      `💡 **مثال:**\n\`https://example.com/large-file.zip\``
    );
    return;
  }

  if (text === '/help') {
    await sendMessage(env, chatId,
      `📖 **راهنمای کامل:**\n\n` +
      `**نحوه استفاده:**\n` +
      `• لینک مستقیم فایل را ارسال کنید\n` +
      `• ربات لینک پروکسی شده را می‌دهد\n` +
      `• روی لینک کلیک کرده یا دانلود کنید\n\n` +
      `🔧 **قابلیت‌ها:**\n` +
      `• فایل‌های با هر سایزی پشتیبانی می‌شود\n` +
      `• امکان ادامه دانلود قطع شده\n` +
      `• سرورهای قدرتمند Cloudflare\n\n` +
      `🛠 **دستورات:**\n` +
      `/start - شروع کار\n` +
      `/help - راهنمایی\n` +
      `/about - درباره ربات`
    );
    return;
  }

  if (text === '/about') {
    await sendMessage(env, chatId,
      `🧩 **درباره ربات:**\n\n` +
      `این ربات از تکنولوژی **Cloudflare Workers** استفاده می‌کند و می‌تواند فایل‌های با هر حجمی را پروکسی کند.\n\n` +
      `🔒 **امنیت پیشرفته:**\n` +
      `• کدگذاری Base64 برای لینک‌ها\n` +
      `• محدودیت نرخ درخواست\n` +
      `• محافظت در برابر حملات DDoS\n\n` +
      `⚡ **مزایا:**\n` +
      `• بدون محدودیت حجم فایل\n` +
      `• پشتیبانی از Range Requests\n` +
      `• سرعت بسیار بالا\n` +
      `• نیم بها برای ایران\n` +
      `• قابلیت ادامه دانلود`
    );
    return;
  }

  if (isValidUrl(text)) {
    await processUrl(env, chatId, text);
  } else {
    await sendMessage(env, chatId, 
      `❌ **لینک نامعتبر!**\n\n` +
      `لطفاً یک لینک معتبر ارسال کنید.\n\n` +
      `💡 **مثال صحیح:**\n\`https://example.com/file.zip\`\n\n` +
      `برای راهنمایی کامل /help را ارسال کنید.`
    );
  }
}

function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

async function processUrl(env, chatId, originalUrl) {
  try {
    // ارسال پیام در حال پردازش
    const processingMsg = await sendMessage(env, chatId, 
      `⏳ **در حال پردازش لینک...**\n\n` +
      `لینک: \`${originalUrl}\`\n\n` +
      `در حال بررسی فایل...`
    );

    // بررسی اولیه فایل
    const fileInfo = await getFileInfo(originalUrl);
    
    if (!fileInfo.accessible) {
      await editMessage(env, chatId, processingMsg.result.message_id,
        `❌ **خطا در دسترسی به فایل!**\n\n` +
        `لینک: \`${originalUrl}\`\n\n` +
        `فایل قابل دسترسی نیست یا وجود ندارد.\n` +
        `لطفاً از صحت لینک اطمینان حاصل کنید.`
      );
      return;
    }

    // تولید لینک پروکسی شده
    const encodedUrl = btoa(originalUrl);
    const proxiedUrl = `https://${env.PROXY_DOMAIN}/proxy?url=${encodedUrl}`;

    // آپدیت پیام با اطلاعات کامل
    await editMessage(env, chatId, processingMsg.result.message_id,
      `✅ **لینک پروکسی شده آماده!**\n\n` +
      `📁 **نام فایل:** \`${fileInfo.filename}\`\n` +
      `📦 **سایز فایل:** ${fileInfo.size}\n` +
      `🔍 **نوع فایل:** ${fileInfo.type}\n\n` +
      `🔗 **لینک اصلی:**\n\`${originalUrl}\`\n\n` +
      `⚡ **لینک پروکسی شده:**\n${proxiedUrl}\n\n` +
      `📋 **برای کپی:**\n\`${proxiedUrl}\`\n\n` +
      `💡 **نکته:** برای دانلود روی لینک بالا کلیک کنید. این لینک از **قابلیت ادامه دانلود** پشتیبانی می‌کند.`
    );

  } catch (error) {
    console.error('Error processing URL:', error);
    await sendMessage(env, chatId,
      `❌ **خطا در پردازش لینک!**\n\n` +
      `خطا: ${error.message}\n\n` +
      `لطفاً:\n` +
      `• از صحت لینک مطمئن شوید\n` +
      `• اطمینان حاصل کنید فایل عمومی است\n` +
      `• مجدداً تلاش کنید\n\n` +
      `در صورت تکرار خطا، از /help استفاده کنید.`
    );
  }
}

async function getFileInfo(url) {
  try {
    const response = await fetch(url, { 
      method: 'HEAD',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    
    if (!response.ok) {
      return {
        accessible: false,
        filename: 'unknown',
        size: 'نامشخص',
        type: 'نامشخص'
      };
    }

    const contentLength = response.headers.get('content-length');
    const contentType = response.headers.get('content-type') || 'نامشخص';
    const contentDisposition = response.headers.get('content-disposition');
    
    let filename = 'file';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?(.+?)"?$/);
      if (match) filename = match[1];
    } else {
      const pathname = new URL(url).pathname;
      filename = pathname.split('/').pop() || 'file';
    }

    let size = 'نامشخص';
    if (contentLength) {
      const bytes = parseInt(contentLength);
      if (bytes < 1024) {
        size = `${bytes} بایت`;
      } else if (bytes < 1024 * 1024) {
        size = `${(bytes / 1024).toFixed(1)} KB`;
      } else if (bytes < 1024 * 1024 * 1024) {
        size = `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      } else {
        size = `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
      }
    }

    return {
      accessible: true,
      filename: filename,
      size: size,
      type: contentType.split(';')[0]
    };

  } catch (error) {
    return {
      accessible: false,
      filename: 'unknown',
      size: 'نامشخص',
      type: 'نامشخص'
    };
  }
}

async function sendMessage(env, chatId, text) {
  const url = `https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'Markdown',
      disable_web_page_preview: false
    })
  });

  return await response.json();
}

async function editMessage(env, chatId, messageId, text) {
  const url = `https://api.telegram.org/bot${env.BOT_TOKEN}/editMessageText`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chat_id: chatId,
      message_id: messageId,
      text: text,
      parse_mode: 'Markdown',
      disable_web_page_preview: false
    })
  });

  return await response.json();
}

async function setWebhook(env) {
  const webhookUrl = `https://${env.PROXY_DOMAIN}`;
  const url = `https://api.telegram.org/bot${env.BOT_TOKEN}/setWebhook?url=${webhookUrl}`;
  
  const response = await fetch(url);
  const result = await response.json();
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  });
}

// هندلر پیشرفته پروکسی با پشتیبانی از فایل‌های بزرگ
async function handleProxyRequest(request) {
  try {
    const url = new URL(request.url);
    const encodedUrl = url.searchParams.get('url');
    
    if (!encodedUrl) {
      return new Response('Missing URL parameter', { status: 400 });
    }
    
    const targetUrl = atob(encodedUrl);
    
    // ایجاد هدرهای جدید برای درخواست
    const headers = new Headers();
    
    // کپی کردن هدرهای مهم از درخواست اصلی
    const rangeHeader = request.headers.get('range');
    if (rangeHeader) {
      headers.set('range', rangeHeader);
    }
    
    headers.set('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    headers.set('accept', '*/*');
    headers.set('accept-encoding', 'identity');
    
    // ایجاد درخواست جدید
    const proxyRequest = new Request(targetUrl, {
      headers: headers,
      method: request.method
    });
    
    // اجرای درخواست
    const response = await fetch(proxyRequest);
    
    // اگر درخواست Range باشد، پاسخ جزئی برمی‌گردانیم
    if (rangeHeader && response.status === 206) {
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('access-control-allow-origin', '*');
      responseHeaders.set('access-control-allow-headers', '*');
      responseHeaders.set('access-control-expose-headers', '*');
      
      return new Response(response.body, {
        status: 206,
        headers: responseHeaders
      });
    }
    
    // برای درخواست‌های عادی
    if (response.ok) {
      const responseHeaders = new Headers(response.headers);
      
      // تنظیم هدرهای CORS برای اجازه دسترسی از همه جا
      responseHeaders.set('access-control-allow-origin', '*');
      responseHeaders.set('access-control-allow-headers', '*');
      responseHeaders.set('access-control-expose-headers', '*');
      
      // اطمینان از اینکه Content-Type صحیح است
      if (!responseHeaders.has('content-type')) {
        responseHeaders.set('content-type', 'application/octet-stream');
      }
      
      // اضافه کردن هدرهای کش برای عملکرد بهتر
      responseHeaders.set('cache-control', 'public, max-age=3600');
      
      return new Response(response.body, {
        status: response.status,
        headers: responseHeaders
      });
    }
    
    return new Response('Proxy Error: ' + response.status, { 
      status: response.status 
    });
    
  } catch (error) {
    console.error('Proxy error:', error);
    return new Response('Error processing request: ' + error.message, { 
      status: 500 
    });
  }
        }
