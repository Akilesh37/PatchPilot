package com.example.customer;

import com.example.customer.model.Customer;
import com.example.customer.controller.CustomerController;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CustomerTest {

    @Test
    public void testCustomerModel() {
        Customer customer = new Customer(100L, "Alice Johnson", "alice@example.com");
        assertEquals(100L, customer.getId());
        assertEquals("Alice Johnson", customer.getName());
        assertEquals("alice@example.com", customer.getEmail());

        customer.setName("Bob Smith");
        assertEquals("Bob Smith", customer.getName());
    }

    @Test
    public void testControllerCreation() {
        CustomerController controller = new CustomerController();
        Customer customer = controller.createCustomer("Charlie", "charlie@example.com");
        assertNotNull(customer);
        assertEquals("Charlie", customer.getName());
    }
}
