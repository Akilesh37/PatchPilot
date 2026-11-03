package com.example.order;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

public class OrderService {
    private boolean initialized = false;

    @PostConstruct
    public void init() {
        this.initialized = true;
    }

    @PreDestroy
    public void cleanup() {
        this.initialized = false;
    }

    public boolean isInitialized() {
        return initialized;
    }

    public Order processOrder(String orderId, double amount) {
        return new Order(orderId, amount);
    }
}
