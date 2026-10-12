@extends('layout')

@section('title', 'Settings')

@section('content')
    <div class="heading-row">
        <div>
            <p class="eyebrow">Preferences</p>
            <h1>Settings</h1>
            <p class="subtitle">Configure monitoring defaults and network preferences.</p>
        </div>
    </div>

    <div class="grid-2">
        <div class="panel">
            <h2>Network</h2>
            <ul class="list">
                <li><strong>Building name:</strong> {{ $buildingName }}</li>
                <li><strong>Database:</strong> {{ $databaseName }}</li>
                <li><strong>Scan subnet:</strong> {{ $scanSubnet }}</li>
                <li><strong>Refresh interval:</strong> {{ $refreshMinutes }} minutes</li>
            </ul>
        </div>

        <div class="panel">
            <h2>Monitoring</h2>
            <ul class="list">
                <li>Default device check interval: 60 seconds</li>
                <li>Alert severity thresholds: warning and critical</li>
                <li>Local discovery enabled</li>
                <li>ML recommendations enabled</li>
            </ul>
        </div>
    </div>
@endsection
