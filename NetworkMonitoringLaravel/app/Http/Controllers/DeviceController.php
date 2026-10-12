<?php

namespace App\Http\Controllers;

use App\Models\MonitoredDevice;
use Illuminate\Http\Request;

class DeviceController extends Controller
{
    // List all devices
    public function index()
    {
        $devices = MonitoredDevice::all();

        return view('devices.index', compact('devices'));
    }

    // Show create device form
    public function create()
    {
        return view('devices.create');
    }

    // Store device in database
    public function store(Request $request)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'target' => 'required|string|max:255',
            'mac_address' => 'nullable|string|max:17',
            'device_type' => 'required|string|max:100',
            'interval_seconds' => 'required|integer|min:1',
            'active' => 'boolean',
        ]);

        MonitoredDevice::create($validated);

        return redirect()->route('devices.index')->with('success', 'Device created successfully');
    }

    // Show specific device
    public function show(MonitoredDevice $device)
    {
        $pingRecords = $device->pingRecords()->latest()->paginate(10);
        $alerts = $device->alerts()->latest()->paginate(10);

        return view('devices.show', compact('device', 'pingRecords', 'alerts'));
    }

    // Show edit form
    public function edit(MonitoredDevice $device)
    {
        return view('devices.edit', compact('device'));
    }

    // Update device
    public function update(Request $request, MonitoredDevice $device)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'target' => 'required|string|max:255',
            'mac_address' => 'nullable|string|max:17',
            'device_type' => 'required|string|max:100',
            'interval_seconds' => 'required|integer|min:1',
            'active' => 'boolean',
        ]);

        $device->update($validated);

        return redirect()->route('devices.index')->with('success', 'Device updated successfully');
    }

    // Delete device
    public function destroy(MonitoredDevice $device)
    {
        $device->delete();

        return redirect()->route('devices.index')->with('success', 'Device deleted successfully');
    }
}
