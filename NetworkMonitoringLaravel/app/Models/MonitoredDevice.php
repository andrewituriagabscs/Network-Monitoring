<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class MonitoredDevice extends Model
{
    use HasFactory;

    protected $fillable = ['name', 'target', 'mac_address', 'device_type', 'interval_seconds', 'active'];

    protected $casts = [
        'active' => 'boolean',
        'interval_seconds' => 'integer',
    ];

    // Relationships
    public function pingRecords()
    {
        return $this->hasMany(PingRecord::class);
    }

    public function alerts()
    {
        return $this->hasMany(Alert::class);
    }

    public function recommendations()
    {
        return $this->hasMany(MLRecommendation::class);
    }
}
