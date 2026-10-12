<?php

namespace App\Http\Controllers;

use App\Models\MonitoredDevice;
use App\Models\PingRecord;

class MonitorController extends Controller
{
    public function index()
    {
        $devices = MonitoredDevice::with('pingRecords')->latest()->get();
        $records = PingRecord::with('device')->latest('recorded_at')->limit(10)->get();

        return view('monitor', compact('devices', 'records'));
    }
}
