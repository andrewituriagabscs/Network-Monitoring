@extends('layout')

@section('title', 'Alerts')

@section('content')
    <div class="heading-row">
        <div>
            <p class="eyebrow">Ping events</p>
            <h1>Alerts</h1>
            <p class="subtitle">Unreachable devices and latency spikes.</p>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>Critical</h3>
            <div class="stat-value">{{ $criticalCount }}</div>
        </div>
        <div class="stat-card">
            <h3>Warning</h3>
            <div class="stat-value">{{ $warningCount }}</div>
        </div>
    </div>

    <div class="panel">
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Device</th>
                        <th>Message</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($alerts as $alert)
                        <tr>
                            <td>{{ $alert->created_at->format('M d, H:i') }}</td>
                            <td>{{ $alert->device?->name ?? 'Unknown device' }}</td>
                            <td>{{ $alert->message }}</td>
                            <td><span class="badge {{ $alert->severity === 'critical' ? 'danger' : ($alert->severity === 'warning' ? 'warning' : 'secondary') }}">{{ ucfirst($alert->severity) }}</span></td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="4">No alerts recorded.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
        {{ $alerts->links() }}
    </div>
@endsection
