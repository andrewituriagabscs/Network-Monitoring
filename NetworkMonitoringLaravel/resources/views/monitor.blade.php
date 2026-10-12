@extends('layout')

@section('title', 'Monitor Devices')

@section('content')
    <div class="heading-row">
        <div>
            <p class="eyebrow">Local network</p>
            <h1>Monitor Devices</h1>
            <p class="subtitle">Discover and manage the active devices on your network.</p>
        </div>
        <a href="{{ route('devices.create') }}" class="btn success">+ Add Device</a>
    </div>

    <div class="panel">
        <div class="toolbar">
            <span class="pill">Network scope: 192.168.1.0/24</span>
            <span class="pill">Active devices: {{ $devices->count() }}</span>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Target</th>
                        <th>Type</th>
                        <th>Interval</th>
                        <th>Status</th>
                        <th>Latest ping</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($devices as $device)
                        <tr>
                            <td>{{ $device->name }}</td>
                            <td>{{ $device->target }}</td>
                            <td>{{ $device->device_type }}</td>
                            <td>{{ $device->interval_seconds }}s</td>
                            <td><span class="badge {{ $device->active ? 'success' : 'secondary' }}">{{ $device->active ? 'Active' : 'Paused' }}</span></td>
                            <td>{{ optional($device->pingRecords()->latest('recorded_at')->first())->recorded_at?->format('M d, H:i') ?? 'No data yet' }}</td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="6">No monitored devices yet.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>

    <div class="panel">
        <div class="heading-row">
            <div>
                <p class="eyebrow">Recent checks</p>
                <h2>Ping history</h2>
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Device</th>
                        <th>Min</th>
                        <th>Median</th>
                        <th>Max</th>
                        <th>Loss</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($records as $record)
                        <tr>
                            <td>{{ $record->recorded_at?->format('M d, H:i') ?? 'N/A' }}</td>
                            <td>{{ $record->device?->name ?? 'Unknown' }}</td>
                            <td>{{ $record->latency_min ?? '—' }}</td>
                            <td>{{ $record->latency_median ?? '—' }}</td>
                            <td>{{ $record->latency_max ?? '—' }}</td>
                            <td>{{ $record->packet_loss ?? 0 }}%</td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="6">No ping data yet.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
@endsection
