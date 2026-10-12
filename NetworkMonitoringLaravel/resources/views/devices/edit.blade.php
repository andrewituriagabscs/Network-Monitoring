@extends('layout')

@section('title', 'Edit Device - ' . $device->name)

@section('content')
    <h2>Edit Device: {{ $device->name }}</h2>

    <div class="card" style="max-width: 600px;">
        <form action="{{ route('devices.update', $device) }}" method="POST">
            @csrf
            @method('PUT')

            <div class="form-group">
                <label for="name">Device Name *</label>
                <input type="text" id="name" name="name" value="{{ old('name', $device->name) }}" required>
                @error('name') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div class="form-group">
                <label for="target">Target (IP/Hostname) *</label>
                <input type="text" id="target" name="target" value="{{ old('target', $device->target) }}" required>
                @error('target') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div class="form-group">
                <label for="mac_address">MAC Address</label>
                <input type="text" id="mac_address" name="mac_address" value="{{ old('mac_address', $device->mac_address) }}">
                @error('mac_address') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div class="form-group">
                <label for="device_type">Device Type *</label>
                <select id="device_type" name="device_type" required>
                    <option value="Router" {{ old('device_type', $device->device_type) == 'Router' ? 'selected' : '' }}>Router</option>
                    <option value="Switch" {{ old('device_type', $device->device_type) == 'Switch' ? 'selected' : '' }}>Switch</option>
                    <option value="Server" {{ old('device_type', $device->device_type) == 'Server' ? 'selected' : '' }}>Server</option>
                    <option value="Workstation" {{ old('device_type', $device->device_type) == 'Workstation' ? 'selected' : '' }}>Workstation</option>
                    <option value="Printer" {{ old('device_type', $device->device_type) == 'Printer' ? 'selected' : '' }}>Printer</option>
                    <option value="IoT" {{ old('device_type', $device->device_type) == 'IoT' ? 'selected' : '' }}>IoT Device</option>
                    <option value="Other" {{ old('device_type', $device->device_type) == 'Other' ? 'selected' : '' }}>Other</option>
                </select>
                @error('device_type') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div class="form-group">
                <label for="interval_seconds">Ping Interval (seconds) *</label>
                <input type="number" id="interval_seconds" name="interval_seconds" value="{{ old('interval_seconds', $device->interval_seconds) }}" min="1" required>
                @error('interval_seconds') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="active" value="1" {{ old('active', $device->active) ? 'checked' : '' }}>
                    Active (monitoring enabled)
                </label>
                @error('active') <span style="color: red; font-size: 12px;">{{ $message }}</span> @enderror
            </div>

            <div style="margin-top: 30px;">
                <button type="submit" class="btn">Update Device</button>
                <a href="{{ route('devices.show', $device) }}" class="btn btn-secondary">Cancel</a>
            </div>
        </form>
    </div>
@endsection
