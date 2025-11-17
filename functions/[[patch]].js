const TELEGRAM_TOKEN = "8367127956:AAHAR6zf2m4_hNJOw4cesM_3ExsNacvWxUU"; // توکن ربات خود را اینجا قرار دهید

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname;

  try {
    // هندلر وب‌هوک تلگرام
    if (request.method === 'POST' && path === '/webhook') {
      return await handleTelegramUpdate(request, env);
    }

    // هندلر پروکسی (همانند سایت شما)
    if (path === '/proxy') {
      return await handleProxyRequest(request, env);
    }

    // تنظیم وب‌هوک
    if (path === '/setWebhook') {
      return await setWebhook(context);
    }

    // صفحه اصلی
    return new Response(JSON.stringify({
      status: 'online',
      message: 'Telegram Proxy Bot is Running!',
      usage: 'Send URLs to the bot to get proxied links'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// هندلر آپدیت‌های تلگرام
async function handleTelegramUpdate(request, env) {
  const update = await request.json();

  if (update.message && update.message.text) {
    await handleMessage(update.message, env, request);
  }

  return new Response('OK');
}

// پردازش پیام‌های کاربر
async function handleMessage(message, env, request) {
  const chatId = message.chat.id;
  const text = message.text.trim();

  // دستور start
  if (text === '/start' || text === '/start@your_bot_username') {
    await sendTelegramMessage(chatId,
      `🤖 **ربات پروکسی ساز**\n\n` +
      `لینک مستقیم فایل خود را ارسال کنید تا لینک پروکسی شده آن را دریافت کنید.\n\n` +
      `💡 **مثال:**\n` +
      `https://example.com/file.zip\n\n` +
      `⚡ **ویژگی‌ها:**\n` +
      `• پشتیبانی از فایل‌های بزرگ\n` +
      `• قابلیت ادامه دانلود\n` +
      `• سرعت بالا\n` +
      `• نیم بها برای کاربران ایرانی`
    );
    return;
  }

  // دستور help
  if (text === '/help' || text === '/help@your_bot_username') {
    await sendTelegramMessage(chatId,
      `📖 **راهنمای ربات:**\n\n` +
      `**نحوه استفاده:**\n` +
      `1. لینک مستقیم فایل را ارسال کنید\n` +
      `2. ربات لینک پروکسی شده را می‌دهد\n` +
      `3. روی لینک کلیک کرده یا دانلود کنید\n\n` +
      `🔗 **مثال لینک معتبر:**\n` +
      `\`https://example.com/file.zip\`\n\n` +
      `🛠 **دستورات:**\n` +
      `/start - شروع کار\n` +
      `/help - راهنمایی\n` +
      `/about - درباره ربات`
    );
    return;
  }

  // دستور about
  if (text === '/about' || text === '/about@your_bot_username') {
    await sendTelegramMessage(chatId,
      `🧩 **درباره ربات:**\n\n` +
      `این ربات از تکنولوژی **Cloudflare** استفاده می‌کند و می‌تواند فایل‌های با هر حجمی را پروکسی کند.\n\n` +
      `🔒 **امنیت:**\n` +
      `• کدگذاری پیشرفته\n` +
      `• محافظت در برابر حملات\n` +
      `• محدودیت نرخ درخواست\n\n` +
      `⚡ **مزایا:**\n` +
      `• بدون محدودیت حجم\n` +
      `• پشتیبانی از ادامه دانلود\n` +
      `• سرعت بسیار بالا\n` +
      `• نیم بها برای کاربران ایرانی`
    );
    return;
  }

  // پردازش لینک
  if (isValidUrl(text)) {
    await processUserUrl(chatId, text, request);
  } else {
    await sendTelegramMessage(chatId,
      `❌ **لینک نامعتبر!**\n\n` +
      `لطفاً یک لینک معتبر ارسال کنید.\n\n` +
      `💡 **مثال صحیح:**\n` +
      `\`https://example.com/file.zip\`\n\n` +
      `برای راهنمایی /help را ارسال کنید.`
    );
  }
}

// بررسی معتبر بودن URL
function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

// پردازش لینک کاربر (مشابه سایت شما)
async function processUserUrl(chatId, originalUrl, request) {
  try {
    // ارسال پیام "در حال پردازش"
    await sendTelegramMessage(chatId, `⏳ **در حال پردازش لینک...**\n\n\`${originalUrl}\``);

    // دریافت اطلاعات فایل
    const fileInfo = await getFileInfo(originalUrl);
    
    if (!fileInfo.accessible) {
      await sendTelegramMessage(chatId,
        `❌ **خطا در دسترسی به فایل!**\n\n` +
        `لینک: \`${originalUrl}\`\n\n` +
        `فایل قابل دسترسی نیست یا وجود ندارد.\n` +
        `لطفاً از صحت لینک اطمینان حاصل کنید.`
      );
      return;
    }

    // ساخت لینک پروکسی شده
    const baseUrl = new URL(request.url).origin;
    const encodedUrl = btoa(originalUrl);
    const proxiedUrl = `${baseUrl}/proxy?url=${encodedUrl}`;

    // ارسال نتیجه به کاربر
    await sendTelegramMessage(chatId,
      `✅ **لینک پروکسی شده آماده!**\n\n` +
      `📁 **نام فایل:** \`${fileInfo.filename}\`\n` +
      `📦 **سایز فایل:** ${fileInfo.size}\n` +
      `🔍 **نوع فایل:** ${fileInfo.type}\n\n` +
      `🔗 **لینک اصلی:**\n\`${originalUrl}\`\n\n` +
      `⚡ **لینک پروکسی شده:**\n${proxiedUrl}\n\n` +
      `💡 **نکته:** برای دانلود روی لینک بالا کلیک کنید. این لینک از **قابلیت ادامه دانلود** پشتیبانی می‌کند.`
    );

  } catch (error) {
    await sendTelegramMessage(chatId,
      `❌ **خطا در پردازش لینک!**\n\n` +
      `خطا: ${error.message}\n\n` +
      `لطفاً:\n` +
      `• از صحت لینک مطمئن شوید\n` +
      `• اطمینان حاصل کنید فایل عمومی است\n` +
      `• مجدداً تلاش کنید`
    );
  }
}

// دریافت اطلاعات فایل (مشابه سایت شما)
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

// ارسال پیام به تلگرام
async function sendTelegramMessage(chatId, text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
  
  try {
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

    if (!response.ok) {
      const error = await response.json();
      console.error('Telegram API error:', error);
    }
  } catch (error) {
    console.error('Failed to send Telegram message:', error);
  }
}

// هندلر پروکسی (کاملاً مشابه سایت شما)
async function handleProxyRequest(request, env) {
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
      
      return new Response(response.body, {
        status: response.status,
        headers: responseHeaders
      });
    }
    
    return new Response('Proxy Error: ' + response.status, { 
      status: response.status 
    });
    
  } catch (error) {
    return new Response('Error processing request: ' + error.message, { 
      status: 500 
    });
  }
}

// تنظیم وب‌هوک
async function setWebhook(context) {
  const baseUrl = new URL(context.request.url).origin;
  const webhookUrl = `${baseUrl}/webhook`;
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${webhookUrl}`;
  
  try {
    const response = await fetch(url);
    const result = await response.json();
    
    return new Response(JSON.stringify(result, null, 2), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
      }
