<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('monitored_devices', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('target')->comment('IP address or hostname');
            $table->string('mac_address')->nullable();
            $table->string('device_type')->comment('Router, Server, Workstation, etc.');
            $table->integer('interval_seconds')->default(60)->comment('Ping interval in seconds');
            $table->boolean('active')->default(true);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('monitored_devices');
    }
};
