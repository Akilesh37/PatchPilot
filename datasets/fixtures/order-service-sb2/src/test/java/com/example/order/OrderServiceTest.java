package com.example.order;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class OrderServiceTest {

    @Test
    public void testOrderProcessing() {
        OrderService service = new OrderService();
        service.init();
        assertTrue(service.isInitialized());

        Order order = service.processOrder("ORD-999", 149.50);
        assertNotNull(order);
        assertEquals("ORD-999", order.getOrderId());
        assertEquals(149.50, order.getAmount(), 0.001);

        service.cleanup();
        assertFalse(service.isInitialized());
    }
}
