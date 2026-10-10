#include "stream_client.h"

RingBuffer::RingBuffer(size_t size) : _size(size), _head(0), _tail(0), _closed(false) {
    _buffer = new uint8_t[size];
}

RingBuffer::~RingBuffer() {
    delete[] _buffer;
}

size_t RingBuffer::available() const {
    size_t h = _head.load();
    size_t t = _tail.load();
    if (h >= t) {
        return h - t;
    }
    return _size - t + h;
}

size_t RingBuffer::freeSpace() const {
    return _size - 1 - available();
}

size_t RingBuffer::write(const uint8_t* data, size_t len) {
    if (_closed) return 0;
    
    size_t space = freeSpace();
    if (len > space) {
        len = space; // truncate if full
    }
    
    for (size_t i = 0; i < len; ++i) {
        _buffer[_head] = data[i];
        _head = (_head + 1) % _size;
    }
    return len;
}

size_t RingBuffer::read(uint8_t* data, size_t len) {
    size_t avail = available();
    if (len > avail) {
        len = avail;
    }
    
    for (size_t i = 0; i < len; ++i) {
        data[i] = _buffer[_tail];
        _tail = (_tail + 1) % _size;
    }
    return len;
}

void RingBuffer::close() {
    _closed = true;
}

bool RingBuffer::isClosed() const {
    return _closed;
}
