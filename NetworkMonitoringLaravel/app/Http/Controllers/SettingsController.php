<?php

namespace App\Http\Controllers;

class SettingsController extends Controller
{
    public function index()
    {
        return view('settings', [
            'buildingName' => config('app.name', 'Network Monitoring System'),
            'databaseName' => env('DB_DATABASE', 'network_monitoring'),
            'scanSubnet' => '192.168.1.0/24',
            'refreshMinutes' => 5,
        ]);
    }
}
