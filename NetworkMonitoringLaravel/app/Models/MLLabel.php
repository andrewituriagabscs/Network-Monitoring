<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class MLLabel extends Model
{
    use HasFactory;

    protected $fillable = ['ping_record_id', 'label'];

    public function pingRecord()
    {
        return $this->belongsTo(PingRecord::class, 'ping_record_id');
    }
}
