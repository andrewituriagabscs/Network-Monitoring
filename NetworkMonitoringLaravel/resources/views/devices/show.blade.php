@extends('layout')

@section('title', 'Device Details - ' . $device->name)

@section('content')
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
        <h2>{{ $device->name }}</h2>
        <div>
            <a href="{{ route('devices.edit', $device) }}" class="btn">Edit</a>
            <a href="{{ route('devices.index') }}" class="btn btn-secondary">Back to Devices</a>
        </div>
    </div>

    <!-- Device Information Card -->
    <div class="card">
        <h3>Device Information</h3>
        <table>
            <tr>
                <td><strong>Name:</strong></td>
                <td>{{ $device->name }}</td>
            </tr>
            <tr>
                <td><strong>Target:</strong></td>
                <td><code>{{ $device->target }}</code></td>
            </tr>
            <tr>
                <td><strong>MAC Address:</strong></td>
                <td>{{ $device->mac_address ?? 'N/A' }}</td>
            </tr>
            <tr>
                <td><strong>Device Type:</strong></td>
                <td>{{ $device->device_type }}</td>
            </tr>
            <tr>
                <td><strong>Ping Interval:</strong></td>
                <td>{{ $device->interval_seconds }} seconds</td>
            </tr>
            <tr>
                <td><strong>Status:</strong></td>
                <td>
                    @if ($device->active)
                        <span class="badge badge-success">● Active (Monitoring Enabled)</span>
                    @else
                        <span class="badge badge-danger">● Inactive (Monitoring Disabled)</span>
                    @endif
                </td>
            </tr>
            <tr>
                <td><strong>Created:</strong></td>
                <td>{{ $device->created_at->format('M d, Y H:i:s') }}</td>
            </tr>
        </table>
    </div>

    <!-- Ping Records Section -->
    <div class="card">
        <h3>Recent Ping Records (Last 10)</h3>
        @if ($pingRecords->count() > 0)
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Min Latency</th>
                        <th>Median Latency</th>
                        <th>Max Latency</th>
                        <th>Packet Loss</th>
                    </tr>
                </thead>
                <tbody>
                    @foreach ($pingRecords as $record)
                        <tr>
                            <td>{{ $record->recorded_at->format('M d, H:i:s') }}</td>
                            <td>
                                <strong>{{ number_format($record->latency_min, 2) }} ms</strong>
                                @if ($record->latency_min > 100)
                                    <span class="badge badge-danger" style="margin-left: 5px;">⚠ High</span>
                                @elseif ($record->latency_min > 50)
                                    <span class="badge" style="background: #fff3cd; color: #856404;">⚠ Medium</span>
                                @else
                                    <span class="badge badge-success">✓ Good</span>
                                @endif
                            </td>
                            <td>{{ number_format($record->latency_median, 2) }} ms</td>
                            <td>{{ number_format($record->latency_max, 2) }} ms</td>
                            <td>{{ number_format($record->packet_loss, 1) }}%</td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
            <div style="margin-top: 10px; text-align: center;">
                {{ $pingRecords->links() }}
            </div>
        @else
            <p style="color: #999;">No ping records yet. Data will appear once monitoring starts.</p>
        @endif
    </div>

    <!-- Alerts Section -->
    <div class="card">
        <h3>Active Alerts</h3>
        @if ($alerts->count() > 0)
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Message</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    @foreach ($alerts as $alert)
                        <tr>
                            <td>{{ $alert->created_at->format('M d, H:i:s') }}</td>
                            <td>{{ $alert->message }}</td>
                            <td>
                                @if (str_contains(strtolower($alert->message), 'critical'))
                                    <span class="badge badge-danger">Critical</span>
                                @elseif (str_contains(strtolower($alert->message), 'warning'))
                                    <span class="badge" style="background: #fff3cd; color: #856404;">Warning</span>
                                @else
                                    <span class="badge">Info</span>
                                @endif
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
            <div style="margin-top: 10px; text-align: center;">
                {{ $alerts->links() }}
            </div>
        @else
            <p style="color: #999;">No active alerts. Device is operating normally.</p>
        @endif
    </div>

    <div style="margin-top: 30px;">
        <form action="{{ route('devices.destroy', $device) }}" method="POST" style="display:inline;">
            @csrf
            @method('DELETE')
            <button type="submit" class="btn btn-danger" onclick="return confirm('Delete this device and all its records? This cannot be undone.')">Delete Device</button>
        </form>
    </div>
@endsection
