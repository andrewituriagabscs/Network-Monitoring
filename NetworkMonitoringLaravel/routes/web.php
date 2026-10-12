<?php

use App\Http\Controllers\AlertController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\DeviceController;
use App\Http\Controllers\MLModelController;
use App\Http\Controllers\MonitorController;
use App\Http\Controllers\PingRecordController;
use App\Http\Controllers\PythonApiController;
use App\Http\Controllers\SettingsController;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return redirect()->route('dashboard');
});

Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');
Route::get('/monitor', [MonitorController::class, 'index'])->name('monitor.index');
Route::get('/alerts', [AlertController::class, 'index'])->name('alerts.index');
Route::get('/ping-records', [PingRecordController::class, 'index'])->name('ping-records.index');
Route::get('/ml-insights', [MLModelController::class, 'index'])->name('ml-insights.index');
Route::get('/settings', [SettingsController::class, 'index'])->name('settings.index');

Route::resource('devices', DeviceController::class);

Route::any('/api/{path}', [PythonApiController::class, 'forward'])->where('path', '.*');
