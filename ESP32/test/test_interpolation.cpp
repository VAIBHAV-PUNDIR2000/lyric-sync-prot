#include <iostream>
#include <vector>
#include <string>
#include <chrono>

struct LyricLine {
    uint32_t t;
    std::string s;
};

// Simulation of the zero-polling anchor system
class LyricSynchronizer {
public:
    void updateAnchor(uint32_t srv_time, uint32_t srv_pos, int new_idx, const std::vector<LyricLine>& new_lines) {
        anchor_local_time = millis();
        anchor_srv_pos = srv_pos;
        idx = new_idx;
        lines = new_lines;
        has_data = true;
    }

    uint32_t getInterpolatedPosition() const {
        if (!has_data) return 0;
        uint32_t now = millis();
        return anchor_srv_pos + (now - anchor_local_time);
    }

    void updateDisplay() {
        if (!has_data || lines.empty()) return;
        
        uint32_t pos = getInterpolatedPosition();
        
        // Advance index if needed
        while (idx + 1 < lines.size() && pos >= lines[idx + 1].t) {
            idx++;
            std::cout << "[LCD] " << lines[idx].s << std::endl;
        }
    }

private:
    uint32_t millis() const {
        // Mock millis based on system time for testing
        auto now = std::chrono::steady_clock::now();
        auto duration = now.time_since_epoch();
        return std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    }

    uint32_t anchor_local_time = 0;
    uint32_t anchor_srv_pos = 0;
    size_t idx = 0;
    std::vector<LyricLine> lines;
    bool has_data = false;
};

int main() {
    LyricSynchronizer sync;
    std::vector<LyricLine> mock_lines = {
        {100, "First Line"},
        {500, "Second Line"},
        {1000, "Third Line"}
    };
    
    // Server says position is 50ms at time T
    sync.updateAnchor(0, 50, -1, mock_lines);
    
    std::cout << "Starting simulation...\n";
    for(int i=0; i<15; i++) {
        // sleep 100ms
        struct timespec ts;
        ts.tv_sec = 0;
        ts.tv_nsec = 100000000;
        nanosleep(&ts, NULL);
        
        sync.updateDisplay();
    }
    std::cout << "Done simulation.\n";
    return 0;
}
