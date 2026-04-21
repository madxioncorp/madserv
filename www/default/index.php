<?php
/**
 * MadServ - Default Welcome Page
 */
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to MadServ</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: #16213e;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            max-width: 600px;
            width: 90%;
        }
        h1 { font-size: 2.5rem; color: #0f3460; margin-bottom: 8px;
             background: linear-gradient(135deg, #667eea, #764ba2);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 24px; }
        .info-card {
            background: #0f3460;
            border-radius: 8px;
            padding: 16px;
            text-align: left;
        }
        .info-card h3 { color: #667eea; font-size: 0.85rem; text-transform: uppercase;
                        letter-spacing: 1px; margin-bottom: 8px; }
        .info-card p { font-size: 0.95rem; word-break: break-all; }
        .badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MadServ</h1>
        <p class="subtitle">Your local development environment is running.</p>
        <div class="info-grid">
            <div class="info-card">
                <h3>PHP Version</h3>
                <p><?= phpversion() ?></p>
            </div>
            <div class="info-card">
                <h3>Server Software</h3>
                <p><?= $_SERVER['SERVER_SOFTWARE'] ?? 'PHP Built-in' ?></p>
            </div>
            <div class="info-card">
                <h3>Document Root</h3>
                <p><?= $_SERVER['DOCUMENT_ROOT'] ?></p>
            </div>
            <div class="info-card">
                <h3>Server Time</h3>
                <p><?= date('Y-m-d H:i:s') ?></p>
            </div>
        </div>
        <span class="badge">MadServ v1.0</span>
        <p style="margin-top:20px; color:#555; font-size:0.8rem;">
            Place your projects in the <strong>www/</strong> folder.
        </p>
    </div>
</body>
</html>
