@extends('layout')

@section('title', 'Monitored Devices')

@section('content')
    <h2>Monitored Devices</h2>
    
    <div style="margin-bottom: 20px;">
        <a href="{{ route('devices.create') }}" class="btn">+ Add New Device</a>
    </div>

    @if ($devices->count() > 0)
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Target</th>
                        <th>MAC Address</th>
                        <th>Type</th>
                        <th>Interval (s)</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    @foreach ($devices as $device)
                        <tr>
                            <td><strong>{{ $device->name }}</strong></td>
                            <td><code>{{ $device->target }}</code></td>
                            <td>{{ $device->mac_address ?? 'N/A' }}</td>
                            <td>{{ $device->device_type }}</td>
                            <td>{{ $device->interval_seconds }}</td>
                            <td>
                                @if ($device->active)
                                    <span class="badge badge-success">● Active</span>
                                @else
                                    <span class="badge badge-danger">● Inactive</span>
                                @endif
                            </td>
                            <td>
                                <a href="{{ route('devices.show', $device) }}" class="btn" style="padding: 5px 10px; font-size: 12px;">View</a>
                                <a href="{{ route('devices.edit', $device) }}" class="btn btn-secondary" style="padding: 5px 10px; font-size: 12px;">Edit</a>
                                <form action="{{ route('devices.destroy', $device) }}" method="POST" style="display:inline;">
                                    @csrf
                                    @method('DELETE')
                                    <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Delete this device?')">Delete</button>
                                </form>
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @else
        <div class="card">
            <p style="color: #999; text-align: center;">No devices configured yet. <a href="{{ route('devices.create') }}">Create one now</a></p>
        </div>
    @endif
@endsection
