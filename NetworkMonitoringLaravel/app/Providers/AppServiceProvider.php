<?php

namespace App\Providers;

use Illuminate\Foundation\DevCommands;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        if (class_exists(DevCommands::class) && $this->app->runningInConsole()) {
            DevCommands::register('python -u ../NetworkMonitoringSystem/app.py', 'python');
        }
    }
}
