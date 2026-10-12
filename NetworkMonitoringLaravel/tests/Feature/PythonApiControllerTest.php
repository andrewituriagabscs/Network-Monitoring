<?php

namespace Tests\Feature;

use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class PythonApiControllerTest extends TestCase
{
    public function test_forwards_json_requests_and_preserves_the_python_response(): void
    {
        Http::fake([
            '127.0.0.1:5000/api/*' => Http::response(['devices' => []], 201),
        ]);

        $response = $this->postJson('/api/devices?source=dashboard', ['devices' => []]);

        $response->assertCreated()->assertJson(['devices' => []]);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'POST'
            && $request->url() === 'http://127.0.0.1:5000/api/devices?source=dashboard'
            && $request['devices'] === []
        );
    }

    public function test_forwards_reclassify_request(): void
    {
        Http::fake([
            '127.0.0.1:5000/api/devices/reclassify' => Http::response(['ok' => true, 'reclassified' => []], 200),
        ]);

        $response = $this->postJson('/api/devices/reclassify');

        $response->assertOk()->assertJson(['ok' => true, 'reclassified' => []]);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'POST'
            && $request->url() === 'http://127.0.0.1:5000/api/devices/reclassify'
        );
    }
}
