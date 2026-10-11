#include "stream_client.h"
#include <cstring>

RingBuffer::RingBuffer(size_t size) : _size(size), _head(0), _tail(0), _closed(false) {
    _buffer = new uint8_t[size];
}

RingBuffer::~RingBuffer() {
    delete[] _buffer;
}

size_t RingBuffer::available() const {
    size_t h = _head.load(std::memory_order_acquire);
    size_t t = _tail.load(std::memory_order_acquire);
    if (h >= t) {
        return h - t;
    }
    return _size - t + h;
}

size_t RingBuffer::freeSpace() const {
    return _size - 1 - available();
}

size_t RingBuffer::write(const uint8_t* data, size_t len) {
    if (_closed.load(std::memory_order_acquire)) return 0;

    size_t h = _head.load(std::memory_order_relaxed);
    size_t t = _tail.load(std::memory_order_acquire);
    size_t space = (t == 0) ? (_size - 1 - h) + 0
                            : (h >= t) ? (_size - 1 - h + t)
                                       : (t - h - 1);
    if (len > space) {
        len = space;
    }
    if (len == 0) return 0;

    // Copy data in up to two segments (wrap-around), then publish _head once.
    size_t first = _size - h;
    if (first > len) first = len;
    memcpy(_buffer + h, data, first);
    if (len > first) {
        memcpy(_buffer, data + first, len - first);
    }
    _head.store((h + len) % _size, std::memory_order_release);
    return len;
}

size_t RingBuffer::read(uint8_t* data, size_t len) {
    size_t t = _tail.load(std::memory_order_relaxed);
    size_t h = _head.load(std::memory_order_acquire);
    size_t avail = (h >= t) ? (h - t) : (_size - t + h);
    if (len > avail) {
        len = avail;
    }
    if (len == 0) return 0;

    // Copy data in up to two segments (wrap-around), then publish _tail once.
    size_t first = _size - t;
    if (first > len) first = len;
    memcpy(data, _buffer + t, first);
    if (len > first) {
        memcpy(data + first, _buffer, len - first);
    }
    _tail.store((t + len) % _size, std::memory_order_release);
    return len;
}

void RingBuffer::close() {
    _closed.store(true, std::memory_order_release);
}

bool RingBuffer::isClosed() const {
    return _closed.load(std::memory_order_acquire);
}
