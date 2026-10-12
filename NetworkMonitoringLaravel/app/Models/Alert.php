<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Alert extends Model
{
    use HasFactory;

    protected $fillable = ['monitored_device_id', 'alert_type', 'message', 'severity', 'resolved', 'resolved_at'];

    protected $casts = [
        'resolved' => 'boolean',
        'resolved_at' => 'datetime',
    ];

    public function device()
    {
        return $this->belongsTo(MonitoredDevice::class, 'monitored_device_id');
    }
}
