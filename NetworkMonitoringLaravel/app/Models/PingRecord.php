<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class PingRecord extends Model
{
    use HasFactory;

    protected $fillable = ['monitored_device_id', 'latency_min', 'latency_median', 'latency_max', 'packet_loss', 'ping_sent', 'ping_received', 'online', 'recorded_at'];

    protected $casts = [
        'recorded_at' => 'datetime',
        'latency_min' => 'float',
        'latency_median' => 'float',
        'latency_max' => 'float',
        'packet_loss' => 'float',
        'ping_sent' => 'integer',
        'ping_received' => 'integer',
        'online' => 'boolean',
    ];

    public function device()
    {
        return $this->belongsTo(MonitoredDevice::class, 'monitored_device_id');
    }

    public function labels()
    {
        return $this->hasMany(MLLabel::class);
    }
}
