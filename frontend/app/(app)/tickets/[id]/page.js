'use client'; import {useParams} from 'next/navigation'; import {TicketDetail} from '@/components/TicketUI'; export default function Detail(){const {id}=useParams();return <TicketDetail id={id}/>}
