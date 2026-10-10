#include <iostream>
#include <cassert>
#include "../src/stream_client.h"

int main() {
    RingBuffer rb(1024);
    assert(rb.available() == 0);
    assert(rb.freeSpace() == 1023); // one byte reserved for empty/full distinguish
    
    const uint8_t data[] = "Hello";
    rb.write(data, 5);
    assert(rb.available() == 5);
    assert(rb.freeSpace() == 1018);
    
    RingBufferStream stream(&rb);
    assert(stream.available() == 5);
    
    uint8_t out[5];
    stream.readBytes(out, 5);
    assert(out[0] == 'H' && out[1] == 'e' && out[2] == 'l' && out[3] == 'l' && out[4] == 'o');
    assert(stream.available() == 0);
    
    std::cout << "All stream_client tests passed!\n";
    return 0;
}
