#ifndef STREAM_CLIENT_H
#define STREAM_CLIENT_H

#include <stddef.h>
#include <stdint.h>
#include <atomic>

#ifdef ARDUINO
#include <Stream.h>
#endif

// A simple ring buffer to safely pass I2S DMA audio to the HTTP client Stream wrapper.
class RingBuffer {
public:
    RingBuffer(size_t size);
    ~RingBuffer();

    // Rule of Three: Prevent double-free heap corruption
    RingBuffer(const RingBuffer&) = delete;
    RingBuffer& operator=(const RingBuffer&) = delete;

    size_t write(const uint8_t* data, size_t len);
    size_t read(uint8_t* data, size_t len);
    size_t available() const;
    size_t freeSpace() const;
    
    // Stop the buffer from accepting more data and signal EOF
    void close();
    bool isClosed() const;

private:
    uint8_t* _buffer;
    size_t _size;
    std::atomic<size_t> _head;
    std::atomic<size_t> _tail;
    std::atomic<bool> _closed;
};

#ifdef ARDUINO
// Inherit from standard Arduino Stream for HTTPClient compatibility
class RingBufferStream : public Stream {
public:
    RingBufferStream(RingBuffer* rb) : _rb(rb) {}

    int available() override {
        return _rb->available();
    }

    int read() override {
        uint8_t c;
        if (_rb->read(&c, 1) == 1) {
            return c;
        }
        return -1;
    }

    int peek() override {
        return -1; // Not implemented/needed for chunked upload
    }

    size_t readBytes(uint8_t *buffer, size_t length) override {
        return _rb->read(buffer, length);
    }
    
    // Required overrides for Stream/Print
    size_t write(uint8_t) override { return 0; }
    void flush() override {}

private:
    RingBuffer* _rb;
};
#else
// Mock interface for native Linux testing without Arduino core
class AbstractStream {
public:
    virtual ~AbstractStream() = default;
    virtual size_t available() = 0;
    virtual int read() = 0;
    virtual size_t readBytes(uint8_t *buffer, size_t length) = 0;
};

class RingBufferStream : public AbstractStream {
public:
    RingBufferStream(RingBuffer* rb) : _rb(rb) {}

    size_t available() override {
        return _rb->available();
    }

    int read() override {
        uint8_t c;
        if (_rb->read(&c, 1) == 1) {
            return c;
        }
        return -1;
    }

    size_t readBytes(uint8_t *buffer, size_t length) override {
        return _rb->read(buffer, length);
    }

private:
    RingBuffer* _rb;
};
#endif

#endif // STREAM_CLIENT_H
