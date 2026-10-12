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
        Schema::create('ping_records', function (Blueprint $table) {
            $table->id();
            $table->foreignId('monitored_device_id')->constrained('monitored_devices')->onDelete('cascade');
            $table->float('latency_min')->nullable()->comment('Minimum latency in ms');
            $table->float('latency_median')->nullable()->comment('Median latency in ms');
            $table->float('latency_max')->nullable()->comment('Maximum latency in ms');
            $table->float('packet_loss')->default(0)->comment('Packet loss percentage');
            $table->integer('ping_sent')->default(0);
            $table->integer('ping_received')->default(0);
            $table->boolean('online')->default(false);
            $table->timestamp('recorded_at')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('ping_records');
    }
};
