<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class MLRecommendation extends Model
{
    use HasFactory;

    protected $fillable = ['monitored_device_id', 'recommendation', 'priority'];

    public function device()
    {
        return $this->belongsTo(MonitoredDevice::class, 'monitored_device_id');
    }
}
