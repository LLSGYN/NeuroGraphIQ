import axios from "axios"
import { ref } from "vue"

export default function useApiService() {
    const error = ref(null);

    async function get_query(query_str:string) {
        console.log(query_str)
        const params = {
            query_str: query_str
        };
        axios.get('http://localhost:5000/exec_query', { params })
        .then(response => {
            console.log(response.data);
        })
        .catch(error => {
            console.error(error);
        });
    }

    async function postUser(userData:string) {
        const params = {
            text: userData
        };
        axios.get('http://localhost:5000/user', { params })
        .then(response => {
            console.log(response.data);
        })
        .catch(error => {
            console.error(error);
        });
    }

    return {
        error,
        postUser,
        get_query
    };
}