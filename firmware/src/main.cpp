#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "stream_client.h"

RingBuffer i2sBuffer(8192);
RingBufferStream streamWrapper(&i2sBuffer);

volatile uint32_t idleCounter = 0;
volatile bool testRunning = true;

// Low priority task to count idle CPU cycles
void idleTask(void *pvParameters) {
    while(testRunning) {
        idleCounter++;
        // Very short delay to prevent watchdog trigger but maximize counting
        delayMicroseconds(10); 
    }
    vTaskDelete(NULL);
}

void setup() {
    Serial.begin(115200);
    delay(100);
    Serial.println("\n--- ESP32 Full Load Benchmark ---");

    uint32_t baselineHeap = ESP.getFreeHeap();
    Serial.printf("[1] Baseline (Core + RingBuffer): %u bytes free\n", baselineHeap);

    // Baseline CPU counting (1 second with NO load)
    Serial.println("Measuring baseline CPU speed...");
    xTaskCreatePinnedToCore(idleTask, "Idle", 2048, NULL, 1, NULL, 1); // Run on App Core
    delay(1000);
    uint32_t baselineCycles = idleCounter;
    idleCounter = 0;
    
    // Simulate Full Load (Wi-Fi + HTTP Client + Streaming)
    Serial.println("Starting Wi-Fi Stack...");
    WiFi.mode(WIFI_STA);
    WiFi.begin("Wokwi-GUEST", "");
    
    // Wait for Wi-Fi connection
    while(WiFi.status() != WL_CONNECTED) {
        delay(100);
    }
    
    uint32_t wifiHeap = ESP.getFreeHeap();
    Serial.printf("[2] Free heap after Wi-Fi connected: %u bytes\n", wifiHeap);
    Serial.printf("    -> Wi-Fi Stack Overhead: %u bytes\n", baselineHeap - wifiHeap);

    // Simulate pushing 32KB of audio while HTTP Client is active
    Serial.println("Simulating HTTP POST with chunked streaming...");
    HTTPClient http;
    http.begin("http://192.168.1.100:8000/identify/stream?compact=true");
    http.addHeader("Content-Type", "audio/pcm; rate=16000");

    uint32_t httpHeap = ESP.getFreeHeap();
    Serial.printf("[3] Free heap during HTTP Client init: %u bytes\n", httpHeap);
    
    // Push data to RingBuffer as if DMA was running
    for(int i = 0; i < 32; i++) {
        uint8_t chunk[1024] = {0};
        i2sBuffer.write(chunk, 1024);
        delay(10); // simulate 16kHz I2S fill time
    }

    uint32_t loadCycles = idleCounter;
    testRunning = false;
    
    float cpuIdlePercent = ((float)loadCycles / baselineCycles) * 100.0;
    float cpuUsedPercent = 100.0 - cpuIdlePercent;
    
    Serial.printf("\n--- RESULTS ---\n");
    Serial.printf("Max RAM Usage (Total): %u bytes (leaving %u bytes free)\n", 
                  327680 - httpHeap, httpHeap);
    Serial.printf("CPU Utilization: %.1f%%\n", cpuUsedPercent);
    Serial.println("Benchmark Complete!");
}

void loop() {
    delay(1000);
}
