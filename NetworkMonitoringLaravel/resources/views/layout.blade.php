<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'Network Monitoring System')</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="app-shell">
        <!-- Sidebar Navigation -->
        <aside class="sidebar" aria-label="Main navigation">
            <div class="brand">
                <span class="brand-mark" aria-hidden="true">🌐</span>
                <span>Network Monitor</span>
            </div>
            <nav class="nav-list">
                <a href="{{ route('dashboard') }}" class="nav-item {{ request()->routeIs('dashboard') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">⌂</span><span>Dashboard</span>
                </a>
                <a href="{{ route('devices.index') }}" class="nav-item {{ request()->routeIs('devices.*') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">◉</span><span>Monitor Devices</span>
                </a>
                <a href="{{ route('alerts.index') }}" class="nav-item {{ request()->routeIs('alerts.*') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">!</span><span>Alerts</span>
                </a>
                <a href="{{ route('ping-records.index') }}" class="nav-item {{ request()->routeIs('ping-records.*') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">▤</span><span>Ping Records</span>
                </a>
                <a href="{{ route('ml-insights.index') }}" class="nav-item {{ request()->routeIs('ml-insights.*') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">⌁</span><span>ML Insights</span>
                </a>
            </nav>
            <nav class="nav-list nav-list-bottom" aria-label="Preferences">
                <a href="{{ route('settings.index') }}" class="nav-item {{ request()->routeIs('settings.*') ? 'active' : '' }}">
                    <span class="nav-icon" aria-hidden="true">⚙</span><span>Settings</span>
                </a>
            </nav>
        </aside>

        <!-- Main Content -->
        <main class="page">
            @if ($message = Session::get('success'))
                <div class="alert alert-success" style="background: #d4edda; border: 1px solid #c3e6cb; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; color: #155724;">
                    {{ $message }}
                </div>
            @endif

            @if ($message = Session::get('error'))
                <div class="alert alert-danger" style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; color: #721c24;">
                    {{ $message }}
                </div>
            @endif

            @if ($errors->any())
                <div class="alert alert-danger" style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; color: #721c24;">
                    <ul style="margin: 0; padding-left: 20px;">
                        @foreach ($errors->all() as $error)
                            <li>{{ $error }}</li>
                        @endforeach
                    </ul>
                </div>
            @endif

            @yield('content')
        </main>
    </div>

    <style>
        /* Alert styles */
        .alert {
            animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Enhanced sidebar for mobile */
        @media (max-width: 768px) {
            .sidebar {
                position: fixed;
                left: 0;
                top: 0;
                width: 244px;
                z-index: 1000;
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .sidebar.open {
                transform: translateX(0);
            }

            .page {
                padding: 24px;
            }
        }
    </style>
</body>
</html>
